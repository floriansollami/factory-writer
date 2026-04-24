from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from factory_writer.application.ports.style_guide_ingestion import (
    DraftStylePackExtractionV1,
    DraftStyleRuleV1,
    PromptRegistryPort,
    PromptSelector,
    StyleGuideChunkCandidate,
    StyleGuideDocumentParserPort,
    StyleGuideDraftPackGeneratorPort,
    StyleGuideDraftPackSnapshot,
    StyleGuideIngestionConfigPort,
    StyleGuideIngestionInput,
    StyleGuideLayoutJobResult,
    StyleGuideLayoutParseResult,
    StyleGuideRepositoryPort,
    StyleGuideStoragePort,
    StyleGuideWorkflowStarterPort,
)
from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    StatutDocumentIngestionRun,
)
from factory_writer.domain.style_guide_types import NiveauContrainte, StatutSource, TypeRegle

_GENERIC_WORKFLOW_FAILURE_MESSAGE = (
    "Le workflow a échoué. Voir l'historique Temporal pour le détail."
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class StyleGuideUploadResult:
    status: StatutSource
    document_source_id: uuid.UUID
    storage_uri: str
    storage_generation: str
    storage_metageneration: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class StyleGuideIngestionStartResult:
    collection_id: uuid.UUID
    ingestion_run_id: uuid.UUID
    document_source_id: uuid.UUID
    storage_uri: str
    workflow_id: str


class StyleGuideIngestionService:
    def __init__(
        self,
        config: StyleGuideIngestionConfigPort,
        repository: StyleGuideRepositoryPort,
        *,
        workflow_starter: StyleGuideWorkflowStarterPort | None = None,
        storage: StyleGuideStoragePort | None = None,
        document_parser: StyleGuideDocumentParserPort | None = None,
        prompt_registry: PromptRegistryPort | None = None,
        draft_pack_generator: StyleGuideDraftPackGeneratorPort | None = None,
    ) -> None:
        self._config = config
        self._repository = repository
        self._workflow_starter = workflow_starter
        self._storage = storage
        self._document_parser = document_parser
        self._prompt_registry = prompt_registry
        self._draft_pack_generator = draft_pack_generator

    async def upload_document_source_pdf(
        self,
        *,
        file_name: str,  # guide-style.pdf
        content: bytes,  # contenu du pdf
        content_type: str,  # application/pdf
    ) -> StyleGuideUploadResult:
        storage = self._require_storage()

        # On génère l'ID métier avant l'upload pour l'utiliser aussi dans le chemin GCS.
        # Le document_source SQL et l'objet stocké dans le bucket partagent ainsi le même identifiant.
        document_source_id = uuid.uuid4()

        uploaded_document_source_file = await storage.upload_document_source_pdf(
            document_source_id=document_source_id,
            file_name=file_name,
            content=content,
            content_type=content_type,
        )

        document_source = await self._repository.create_document_source(
            # Même UUID métier que celui injecté dans le chemin GCS.
            # Exemple: 550e8400-e29b-41d4-a716-446655440000
            document_source_id=document_source_id,
            # URI complète persistée pour les lectures ultérieures.
            # Exemple: gs://factory-writer-style-guide-test/sources/style-guides/550e8400-e29b-41d4-a716-446655440000/guide-style.pdf
            storage_uri=uploaded_document_source_file.storage_uri,
            # Nom du bucket GCS déjà séparé par le StorageClient.
            # Exemple: factory-writer-style-guide-test
            storage_bucket=uploaded_document_source_file.storage_bucket,
            # Chemin objet GCS déjà séparé par le StorageClient.
            # Exemple: sources/style-guides/550e8400-e29b-41d4-a716-446655440000/guide-style.pdf
            storage_object_name=uploaded_document_source_file.storage_object_name,
            # Nom de fichier d'origine reçu depuis le formulaire upload.
            # Exemple: guide-style.pdf
            original_file_name=file_name,
            # Content type que l'API a validé comme PDF.
            # Exemple: application/pdf
            storage_content_type=content_type,
            # Taille brute du PDF en octets.
            # Exemple: 1245860
            storage_size_bytes=len(content),
            # Version du contenu retournée par GCS.
            # Exemple: 1713712543982451
            storage_generation=uploaded_document_source_file.generation,
            # Version des métadonnées retournée par GCS.
            # Exemple: 1
            storage_metageneration=uploaded_document_source_file.metageneration,
        )

        if document_source.storage_generation is None:
            raise RuntimeError("storage_generation manquante apres creation du document source.")
        if document_source.storage_metageneration is None:
            raise RuntimeError(
                "storage_metageneration manquante apres creation du document source."
            )

        return StyleGuideUploadResult(
            status=document_source.statut,
            document_source_id=document_source.id,
            storage_uri=document_source.storage_uri,
            storage_generation=document_source.storage_generation,
            storage_metageneration=document_source.storage_metageneration,
            created_at=_require_datetime(document_source.created_at, "created_at"),
            updated_at=_require_datetime(document_source.updated_at, "updated_at"),
        )

    async def reupload_document_source_pdf(
        self,
        *,
        replaced_document_source_id: uuid.UUID,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> StyleGuideUploadResult:
        storage = self._require_storage()

        replaced_document_source = await self._repository.get_document_source_by_id(
            replaced_document_source_id
        )

        if replaced_document_source is None:
            raise KeyError(str(replaced_document_source_id))

        if replaced_document_source.replaced_by_source_id is not None:
            raise RuntimeError("Ce guide de style a déjà été remplacé.")

        latest_run = await self._repository.get_latest_ingestion_run_for_document_source(
            replaced_document_source.id
        )

        if latest_run is not None and latest_run.statut == StatutDocumentIngestionRun.EN_COURS:
            raise RuntimeError(
                "Ce guide de style est en cours d'ingestion et ne peut pas être re-uploadé."
            )

        document_source_id = uuid.uuid4()
        uploaded_document_source_file = await storage.upload_document_source_pdf(
            document_source_id=document_source_id,
            file_name=file_name,
            content=content,
            content_type=content_type,
        )

        document_source = await self._repository.create_reuploaded_document_source(
            replaced_document_source_id=replaced_document_source_id,
            document_source_id=document_source_id,
            storage_uri=uploaded_document_source_file.storage_uri,
            storage_bucket=uploaded_document_source_file.storage_bucket,
            storage_object_name=uploaded_document_source_file.storage_object_name,
            original_file_name=file_name,
            storage_content_type=content_type,
            storage_size_bytes=len(content),
            storage_generation=uploaded_document_source_file.generation,
            storage_metageneration=uploaded_document_source_file.metageneration,
        )

        if document_source.storage_generation is None:
            raise RuntimeError("storage_generation manquante apres creation du document source.")

        if document_source.storage_metageneration is None:
            raise RuntimeError(
                "storage_metageneration manquante apres creation du document source."
            )

        return StyleGuideUploadResult(
            status=document_source.statut,
            document_source_id=document_source.id,
            storage_uri=document_source.storage_uri,
            storage_generation=document_source.storage_generation,
            storage_metageneration=document_source.storage_metageneration,
            created_at=_require_datetime(document_source.created_at, "created_at"),
            updated_at=_require_datetime(document_source.updated_at, "updated_at"),
        )

    async def start_ingestion(
        self, document_source_id: uuid.UUID
    ) -> StyleGuideIngestionStartResult:
        preparation = await self._repository.prepare_ingestion_start(
            document_source_id=document_source_id,
            pipeline_kind="STYLE_GUIDE_EXTRACTION",
        )
        document_source = preparation.document_source
        run = preparation.run

        logger.info(
            "Style guide | Ingestion | run préparé",
            document_source_id=str(document_source.id),
            collection_id=str(document_source.collection_id),
            ingestion_run_id=str(run.id),
            reused_existing_run=preparation.reused_existing_run,
        )

        if preparation.reused_existing_run:
            logger.info(
                "Style guide | Ingestion | run existant réutilisé",
                document_source_id=str(document_source.id),
                ingestion_run_id=str(run.id),
                workflow_id=run.temporal_workflow_id,
            )
            return StyleGuideIngestionStartResult(
                collection_id=document_source.collection_id,
                ingestion_run_id=run.id,
                document_source_id=document_source.id,
                storage_uri=document_source.storage_uri,
                workflow_id=run.temporal_workflow_id,
            )

        try:
            if self._workflow_starter is None:
                raise RuntimeError("workflow starter non configuré")

            workflow_payload = StyleGuideIngestionInput(
                collection_id=document_source.collection_id,
                document_source_id=document_source.id,
                ingestion_run_id=run.id,
                storage_uri=document_source.storage_uri,
            )

            logger.info(
                "Style guide | Ingestion | démarrage du workflow",
                document_source_id=str(document_source.id),
                collection_id=str(document_source.collection_id),
                ingestion_run_id=str(run.id),
                workflow_id=run.temporal_workflow_id,
            )

            started_workflow_id = await self._workflow_starter.start_style_guide_ingestion(
                workflow_payload
            )

            if started_workflow_id != run.temporal_workflow_id:
                raise RuntimeError(
                    "Workflow Temporal demarre avec un workflow_id different du run d'ingestion."
                )
            logger.info(
                "Style guide | Ingestion | workflow lancé",
                document_source_id=str(document_source.id),
                collection_id=str(document_source.collection_id),
                ingestion_run_id=str(run.id),
                workflow_id=started_workflow_id,
            )
        except Exception as exc:
            logger.exception(
                "Style guide | Ingestion | échec au lancement du workflow",
                document_source_id=str(document_source.id),
                collection_id=str(document_source.collection_id),
                ingestion_run_id=str(run.id),
            )
            await self._repository.update_ingestion_run_status(
                run.id,
                statut=StatutDocumentIngestionRun.ERREUR,
                error_message=str(exc),
                completed_at=datetime.now(UTC),
            )
            raise

        return StyleGuideIngestionStartResult(
            collection_id=document_source.collection_id,
            ingestion_run_id=run.id,
            document_source_id=document_source.id,
            storage_uri=document_source.storage_uri,
            workflow_id=run.temporal_workflow_id,
        )

    async def mark_ingestion_failed(
        self,
        *,
        ingestion_run_id: uuid.UUID,
        message: str | None = None,
    ) -> None:
        logger.error(
            "Style guide | Ingestion | échec",
            ingestion_run_id=str(ingestion_run_id),
            message=message or _GENERIC_WORKFLOW_FAILURE_MESSAGE,
        )
        await self._repository.update_ingestion_run_status(
            ingestion_run_id,
            statut=StatutDocumentIngestionRun.ERREUR,
            error_message=message or _GENERIC_WORKFLOW_FAILURE_MESSAGE,
            completed_at=datetime.now(UTC),
        )

    async def finalize_style_pack_approval(
        self,
        *,
        style_pack_id: uuid.UUID,
    ) -> str:
        logger.info(
            "Style guide | Pack | approbation démarrée",
            style_pack_id=str(style_pack_id),
        )

        # vérifie qu’il ne reste aucune règle A_VALIDER
        # statut du pack = ACTIF
        # chaque regle = APPROUVEE/DESACTIVEE => est_actif TRUE/FALSE
        # document_ingestion_run statut = TERMINE
        # document_source.statut = TERMINE
        # document_collection.statut = TERMINE
        pack = await self._repository.finalize_style_pack_approval(style_pack_id=style_pack_id)

        logger.info(
            "Style guide | Pack | approbation terminée",
            style_pack_id=str(pack.id),
        )

        return str(pack.id)

    async def finalize_style_pack_rejection(
        self,
        *,
        style_pack_id: uuid.UUID,
    ) -> str:
        logger.info(
            "Style guide | Pack | rejet démarré",
            style_pack_id=str(style_pack_id),
        )

        # marque le pack comme non actif et l’archive
        # document_ingestion_run statut = ANNULE
        # document_ingestion_run current_step reste = HUMAN_REVIEW
        # document_ingestion_run completed_at = now()
        # document_source.statut = TERMINE
        # document_collection.statut = TERMINE
        # recalcul du validation_summary_json du pack

        pack = await self._repository.finalize_style_pack_rejection(style_pack_id=style_pack_id)

        logger.info(
            "Style guide | Pack | rejet terminé",
            style_pack_id=str(pack.id),
        )

        return str(pack.id)

    async def start_document_layout_parse(
        self,
        payload: StyleGuideIngestionInput,
    ) -> StyleGuideLayoutJobResult:
        storage = self._require_storage()
        parser = self._require_document_parser()

        logger.info(
            "Style guide | Document AI | préparation",
            ingestion_run_id=str(payload.ingestion_run_id),
            document_source_id=str(payload.document_source_id),
            storage_uri=payload.storage_uri,
        )

        # La generation GCS distingue deux PDFs différents même s'ils ont le même nom.
        document_source_file = await storage.get_document_source_file(payload.storage_uri)

        if document_source_file is None:
            raise FileNotFoundError(f"Objet Cloud Storage introuvable: {payload.storage_uri}")

        # TODO POC+ : ajouter un garde anti double lancement Document AI
        # en cas de replay Temporal après crash du worker.

        # on construit l’URI GCS du dossier de sortie technique où Document AI va écrire le résultat de parsing pour ce PDF précis et cette version précise du PDF

        parser_result_uri = storage.build_parser_result_uri(
            payload.storage_uri,
            "style-guide-layout",
            payload.document_source_id,
            document_source_file.generation,
        )

        parse_result = await parser.start_document_layout_parse(
            input_uri=payload.storage_uri,
            output_uri=parser_result_uri,
        )

        logger.info(
            "Style guide | Document AI | job soumis",
            ingestion_run_id=str(payload.ingestion_run_id),
            document_source_id=str(payload.document_source_id),
            operation_id=parse_result.operation_id,
            parser_resource_name=parse_result.processor_resource_name,
            output_uri=parse_result.output_uri,
        )

        await self._repository.record_layout_parse_result(
            run_id=payload.ingestion_run_id,
            parser_resource_id=parse_result.processor_resource_name,
            operation_id=parse_result.operation_id,
            output_uri=parse_result.output_uri,
        )

        logger.info(
            "Style guide | Document AI | job enregistré en base",
            ingestion_run_id=str(payload.ingestion_run_id),
            document_source_id=str(payload.document_source_id),
            operation_id=parse_result.operation_id,
        )

        return StyleGuideLayoutJobResult(
            collection_id=payload.collection_id,
            document_source_id=payload.document_source_id,
            ingestion_run_id=payload.ingestion_run_id,
            operation_id=parse_result.operation_id,
            output_uri=parse_result.output_uri,
        )

    async def check_document_layout_parse(
        self,
        payload: StyleGuideLayoutJobResult,
    ) -> StyleGuideLayoutParseResult | None:
        storage = self._require_storage()
        parser = self._require_document_parser()

        # vérifie que le job Document AI est terminé avec succès et fournit l’output_uri.
        parse_result = await parser.check_document_layout_parse(
            operation_id=payload.operation_id,
            output_uri=payload.output_uri,
        )

        # dans ce cas on ne fait rien et on laisse le workflow réessayer plus tard
        if parse_result is None:
            return None

        # vérifie qu’un artefact réel existe bien dans GCS sous cet output_uri
        if not await storage.has_parser_result(parse_result.output_uri):
            raise RuntimeError(
                f"Document AI n'a produit aucun JSON exploitable sous {parse_result.output_uri}"
            )

        #  enregistre en base que l’étape de layout parse a abouti pour ce run.
        await self._repository.record_layout_parse_result(
            run_id=payload.ingestion_run_id,
            parser_resource_id=parse_result.processor_resource_name,
            operation_id=parse_result.operation_id,
            output_uri=parse_result.output_uri,
        )

        return StyleGuideLayoutParseResult(
            collection_id=payload.collection_id,
            document_source_id=payload.document_source_id,
            ingestion_run_id=payload.ingestion_run_id,
            output_uri=parse_result.output_uri,
        )

    async def generate_draft_pack(
        self,
        payload: StyleGuideLayoutParseResult,
    ) -> StyleGuideDraftPackSnapshot:
        parser = self._require_document_parser()
        prompt_registry = self._require_prompt_registry()
        draft_pack_generator = self._require_draft_pack_generator()

        logger.info(
            "Style guide | Draft pack | préparation",
            ingestion_run_id=str(payload.ingestion_run_id),
            document_source_id=str(payload.document_source_id),
            output_uri=payload.output_uri,
        )

        try:
            # mettre à jour l’état courant du run
            # puis propager un état cohérent au document source et au document collection
            #  current_step passe de LAYOUT_PARSE à LLM_DRAFT_PACK
            # statut reste EN_COURS
            await self._repository.update_ingestion_run_status(
                payload.ingestion_run_id,
                statut=StatutDocumentIngestionRun.EN_COURS,
                current_step=CurrentStep.LLM_DRAFT_PACK,
                clear_error=True,
            )

            logger.info(
                "Style guide | Draft pack | statut du run mis à jour",
                ingestion_run_id=str(payload.ingestion_run_id),
                current_step=CurrentStep.LLM_DRAFT_PACK.value,
            )

            # on lit la sortie parser de Document AI dans GCS
            # et on la convertit en chunks applicatifs exploitables par le prompt LLM
            chunks = await parser.extract_chunks(payload.output_uri)

            logger.info(
                "Style guide | Draft pack | chunks extraits",
                ingestion_run_id=str(payload.ingestion_run_id),
                document_source_id=str(payload.document_source_id),
                chunk_count=len(chunks),
                provider_ids_preview=_chunk_provider_ids_preview(chunks),
            )

            if not chunks:
                raise RuntimeError(
                    f"Aucun chunk exploitable n'a ete extrait depuis {payload.output_uri}"
                )

            taxonomies = await self._repository.list_taxonomies()

            logger.info(
                "Style guide | Draft pack | taxonomie chargée",
                ingestion_run_id=str(payload.ingestion_run_id),
                taxonomy_count=len(taxonomies),
            )

            prompt = await prompt_registry.get_prompt(
                PromptSelector(
                    name=self._config.draft_pack_prompt_name,
                    version=self._config.active_prompt_version,
                )
            )

            logger.info(
                "Style guide | Draft pack | prompt chargé",
                ingestion_run_id=str(payload.ingestion_run_id),
                prompt_name=prompt.name,
                prompt_version=prompt.version,
                prompt_provider=prompt.registry_provider,
            )

            prepared_prompt = prompt.compile(
                {
                    "chunks_json": json.dumps(
                        [
                            {
                                "source_evidence_provider_id": chunk.provider_id,
                                "index_chunk": chunk.index_chunk,
                                "contenu": chunk.contenu,
                                "page_start": chunk.page_start,
                                "page_end": chunk.page_end,
                            }
                            for chunk in chunks
                        ],
                        ensure_ascii=False,
                    ),
                    "taxonomies_json": json.dumps(
                        {
                            "familles_autorisees": [
                                {
                                    "famille_code": taxonomy.famille_code,
                                    "libelle_fr": taxonomy.libelle_fr,
                                }
                                for taxonomy in taxonomies
                            ]
                        },
                        ensure_ascii=False,
                    ),
                }
            )

            logger.info(
                "Style guide | Draft pack | appel LLM démarré",
                ingestion_run_id=str(payload.ingestion_run_id),
                model=prepared_prompt.llm_config.model,
                chunk_count=len(chunks),
                temperature=prepared_prompt.llm_config.temperature,
                max_tokens=prepared_prompt.llm_config.max_tokens,
                reasoning_level=prepared_prompt.llm_config.reasoning_level,
            )

            # Appeler le LLM avec un prompt prêt à l'exécution.
            # POC: on utilise LiteLLM via le SDK Python direct pour rester simple.
            # Cible prod: le même port pourra appeler un LiteLLM Proxy avec model profiles.
            # via GOOGLE_APPLICATION_CREDENTIALS pour vertex
            generation_result = await draft_pack_generator.generate_draft_pack(
                prompt=prepared_prompt,
            )

            logger.info(
                "Style guide | Draft pack | appel LLM terminé",
                ingestion_run_id=str(payload.ingestion_run_id),
                model=generation_result.metadata.llm_model,
                prompt_name=generation_result.metadata.prompt_name,
                prompt_version=generation_result.metadata.prompt_version,
            )

            # Validation déterministe: provenance, taxonomie, contraintes métier et déduplication.
            candidate = _validate_draft_pack_candidate(
                candidate=generation_result.candidate,
                chunk_contents={chunk.provider_id: chunk.contenu for chunk in chunks},
                famille_codes={taxonomy.famille_code for taxonomy in taxonomies},
            )

            logger.info(
                "Style guide | Draft pack | candidat validé",
                ingestion_run_id=str(payload.ingestion_run_id),
                rule_count=len(candidate.regles),
            )

            snapshot = await self._repository.replace_draft_style_pack(
                document_source_id=payload.document_source_id,
                ingestion_run_id=payload.ingestion_run_id,
                chunks=chunks,
                candidate=candidate,
                metadata=generation_result.metadata,
            )

            logger.info(
                "Style guide | Draft pack | persisté",
                ingestion_run_id=str(payload.ingestion_run_id),
                document_source_id=str(payload.document_source_id),
                draft_pack_id=snapshot.draft_pack_id,
            )

            return snapshot
        except Exception:
            logger.exception(
                "Style guide | Draft pack | échec",
                ingestion_run_id=str(payload.ingestion_run_id),
                document_source_id=str(payload.document_source_id),
            )
            raise

    def _require_storage(self) -> StyleGuideStoragePort:
        if self._storage is None:
            raise RuntimeError("Storage adapter non initialise.")
        return self._storage

    def _require_document_parser(self) -> StyleGuideDocumentParserPort:
        if self._document_parser is None:
            raise RuntimeError("Document Parser non initialise.")
        return self._document_parser

    def _require_prompt_registry(self) -> PromptRegistryPort:
        if self._prompt_registry is None:
            raise RuntimeError("Prompt Registry non initialise.")
        return self._prompt_registry

    def _require_draft_pack_generator(self) -> StyleGuideDraftPackGeneratorPort:
        if self._draft_pack_generator is None:
            raise RuntimeError("Draft Pack Generator adapter non initialise.")
        return self._draft_pack_generator


def _validate_draft_pack_candidate(
    *,
    candidate: DraftStylePackExtractionV1,
    chunk_contents: Mapping[str, str],
    famille_codes: set[str],
) -> DraftStylePackExtractionV1:
    validated_rules: list[DraftStyleRuleV1] = []
    seen_rules: dict[tuple[str, str | None, str], NiveauContrainte] = {}

    for rule in candidate.regles:
        normalized_rule = _normalize_and_validate_rule(
            rule=rule,
            chunk_contents=chunk_contents,
            famille_codes=famille_codes,
        )

        duplicate_key = _rule_duplicate_key(normalized_rule)
        previous_constraint = seen_rules.get(duplicate_key)

        if previous_constraint == normalized_rule.niveau_contrainte:
            continue

        if previous_constraint is not None:
            raise ValueError("Regle de style dupliquee avec niveaux de contrainte contradictoires.")

        seen_rules[duplicate_key] = normalized_rule.niveau_contrainte

        validated_rules.append(normalized_rule)

    if not validated_rules:
        raise ValueError("Aucune regle de style exploitable apres validation.")

    return candidate.model_copy(
        update={
            "regles": validated_rules,
        }
    )


def _chunk_provider_ids_preview(chunks: list[StyleGuideChunkCandidate]) -> list[str]:
    return [chunk.provider_id for chunk in chunks[:5]]


def _normalize_and_validate_rule(
    *,
    rule: DraftStyleRuleV1,
    chunk_contents: Mapping[str, str],
    famille_codes: set[str],
) -> DraftStyleRuleV1:
    chunk_content = chunk_contents.get(rule.source_evidence_provider_id)

    if chunk_content is None:
        raise ValueError(f"source_evidence_provider_id inconnu: {rule.source_evidence_provider_id}")

    citation_source = _normalize_required_text(rule.citation_source, "citation_source")

    if _normalize_for_evidence(citation_source) not in _normalize_for_evidence(chunk_content):
        raise ValueError("citation_source introuvable dans le chunk reference.")

    famille_code = _normalize_optional_text(rule.famille_code)

    if famille_code is not None and famille_code not in famille_codes:
        raise ValueError(f"famille_code inconnu: {famille_code}")

    niveau_contrainte = rule.niveau_contrainte

    match rule.type_regle:
        case TypeRegle.VOIX:
            # Une règle de voix est globale par définition: elle ne cible pas une famille produit.
            famille_code = None
        case TypeRegle.TON if famille_code is None:
            raise ValueError("Une regle TON doit cibler une famille produit.")
        case TypeRegle.PROMESSE_INTERDITE:
            # Une promesse interdite est toujours bloquante, même si le LLM la sort en SOFT.
            niveau_contrainte = NiveauContrainte.HARD

    return rule.model_copy(
        update={
            "texte_regle": _normalize_required_text(rule.texte_regle, "texte_regle"),
            "citation_source": citation_source,
            "famille_code": famille_code,
            "niveau_contrainte": niveau_contrainte,
        }
    )


def _rule_duplicate_key(rule: DraftStyleRuleV1) -> tuple[str, str | None, str]:
    return (
        rule.type_regle.value,
        rule.famille_code,
        rule.texte_regle.casefold(),
    )


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized_value = _normalize_optional_text(value)

    if normalized_value is None:
        raise ValueError(f"{field_name} vide.")

    return normalized_value


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = " ".join(value.split())

    return normalized_value or None


def _normalize_for_evidence(value: str) -> str:
    return " ".join(value.casefold().split())


def _require_datetime(value: datetime | None, field_name: str) -> datetime:
    if value is None:
        raise RuntimeError(f"{field_name} manquant apres creation du document source.")
    return value
