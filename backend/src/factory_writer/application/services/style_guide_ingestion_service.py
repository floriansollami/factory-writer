from __future__ import annotations

import json
import uuid
from collections.abc import Mapping

import structlog

from factory_writer.application.ports.style_guide_ingestion import (
    DraftStylePackExtractionV1,
    DraftStyleRuleV1,
    PromptRegistryPort,
    PromptSelector,
    StyleGuideChunkPersistResult,
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
from factory_writer.domain.style_guide_types import NiveauContrainte, StatutSource, TypeRegle

logger = structlog.get_logger(__name__)

_GENERIC_WORKFLOW_FAILURE_MESSAGE = (
    "Le workflow a échoué. Voir l'historique Temporal pour le détail."
)


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

    async def start_from_storage_event(
        self,
        *,
        bucket_name: str,
        file_name: str,
        target_uri: str,
    ) -> None:
        if bucket_name != self._config.bucket_name:
            raise ValueError(
                f"Wrong bucket: expected {self._config.bucket_name}, got {bucket_name}"
            )

        if file_name.startswith("_factory_writer/"):
            logger.info(
                "style_guide_ingestion.internal_object_ignored",
                bucket_name=bucket_name,
                file_name=file_name,
            )
            return

        if not file_name.lower().endswith(".pdf"):
            raise ValueError(f"File must be a PDF: {file_name}")

        existing_source = await self._repository.get_by_uri(target_uri)

        if existing_source is not None and existing_source.statut != StatutSource.ERREUR:
            raise RuntimeError(f"Style guide already ingested or in progress: {target_uri}")

        if existing_source is None:
            source = await self._repository.create_source(target_uri)
        else:
            source = await self._repository.update_source_status(
                existing_source.id,
                StatutSource.EN_ATTENTE,
                error_message=None,
            )

        workflow_payload = StyleGuideIngestionInput(
            source_id=source.id,
            file_uri=source.uri_fichier,
        )

        try:
            if self._workflow_starter is None:
                raise RuntimeError("workflow starter non configuré")

            workflow_id = await self._workflow_starter.start_style_guide_ingestion(workflow_payload)
        except Exception as exc:
            await self._repository.update_source_status(
                source.id,
                StatutSource.ERREUR,
                error_message=str(exc),
            )
            raise

        logger.info(
            "style_guide_ingestion.started",
            source_id=str(source.id),
            file_uri=source.uri_fichier,
            workflow_id=workflow_id,
        )

    async def mark_source_in_progress(self, source_id: uuid.UUID) -> None:
        await self._repository.update_source_status(
            source_id=source_id,
            statut=StatutSource.EN_COURS,
            only_if_not_terminal=True,
        )

    async def mark_source_failed(
        self,
        source_id: uuid.UUID,
        message: str | None = None,
    ) -> None:
        await self._repository.update_source_status(
            source_id=source_id,
            statut=StatutSource.ERREUR,
            error_message=message or _GENERIC_WORKFLOW_FAILURE_MESSAGE,
        )

    async def start_layout_parse(
        self,
        payload: StyleGuideIngestionInput,
    ) -> StyleGuideLayoutJobResult:
        storage = self._require_storage()
        parser = self._require_document_parser()

        # La generation GCS distingue deux PDFs différents même s'ils ont le même nom.
        source_file = await storage.get_source_file(payload.file_uri)

        if source_file is None:
            raise FileNotFoundError(f"Objet Cloud Storage introuvable: {payload.file_uri}")

        # TODO POC+ : ajouter un garde anti double lancement Document AI
        # en cas de replay Temporal après crash du worker.

        await self._repository.update_storage_metadata(
            source_id=payload.source_id,
            uri=source_file.uri,
            generation=source_file.generation,
            metageneration=source_file.metageneration,
        )

        parser_result_uri = storage.build_parser_result_uri(
            payload.file_uri,
            "style-guide-layout",
            payload.source_id,
            source_file.generation,
        )

        parse_result = await parser.start_layout_extraction(
            input_uri=payload.file_uri,
            output_uri=parser_result_uri,
        )

        await self._repository.update_parser_output(
            source_id=payload.source_id,
            parser_resource_id=parse_result.processor_resource_name,
            operation_id=parse_result.operation_id,
            output_uri=parse_result.output_uri,
        )

        return StyleGuideLayoutJobResult(
            source_id=payload.source_id,
            operation_id=parse_result.operation_id,
            output_uri=parse_result.output_uri,
        )

    async def check_layout_parse(
        self,
        payload: StyleGuideLayoutJobResult,
    ) -> StyleGuideLayoutParseResult | None:
        storage = self._require_storage()
        parser = self._require_document_parser()

        parse_result = await parser.check_layout_extraction(
            operation_id=payload.operation_id,
            output_uri=payload.output_uri,
        )

        if parse_result is None:
            return None

        if not await storage.has_parser_result(parse_result.output_uri):
            raise RuntimeError(
                f"Document AI n'a produit aucun JSON exploitable sous {parse_result.output_uri}"
            )

        await self._repository.update_parser_output(
            source_id=payload.source_id,
            parser_resource_id=parse_result.processor_resource_name,
            operation_id=parse_result.operation_id,
            output_uri=parse_result.output_uri,
        )

        return StyleGuideLayoutParseResult(
            source_id=payload.source_id,
            output_uri=parse_result.output_uri,
        )

    async def persist_fragments(
        self,
        payload: StyleGuideLayoutParseResult,
    ) -> StyleGuideChunkPersistResult:
        parser = self._require_document_parser()

        fragments = await parser.extract_fragments(payload.output_uri)

        if not fragments:
            raise RuntimeError(
                f"Aucun fragment exploitable n'a ete extrait depuis {payload.output_uri}"
            )

        return await self._repository.replace_fragments(
            source_id=payload.source_id,
            fragments=fragments,
        )

    async def generate_draft_pack(
        self,
        payload: StyleGuideChunkPersistResult,
    ) -> StyleGuideDraftPackSnapshot:
        prompt_registry = self._require_prompt_registry()
        draft_pack_generator = self._require_draft_pack_generator()

        fragments = await self._repository.get_fragments_by_ids(payload.fragment_ids)

        if len(fragments) != len(payload.fragment_ids):
            raise ValueError("Certains fragments du guide de style sont introuvables.")

        if any(fragment.source_id != payload.source_id for fragment in fragments):
            raise ValueError("Les fragments ne correspondent pas tous a la source style guide.")

        taxonomies = await self._repository.list_taxonomies()

        prompt = await prompt_registry.get_prompt(
            PromptSelector(
                name=self._config.draft_pack_prompt_name,
                version=self._config.active_prompt_version,
            )
        )

        prepared_prompt = prompt.compile(
            {
                "fragments_json": json.dumps(
                    [
                        {
                            "fragment_source_id": str(fragment.id),
                            "index_fragment": fragment.index_fragment,
                            "contenu": fragment.contenu,
                        }
                        for fragment in fragments
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

        # Appeler le LLM avec un prompt prêt à l'exécution.
        # POC: on utilise LiteLLM via le SDK Python direct pour rester simple.
        # Cible prod: le même port pourra appeler un LiteLLM Proxy avec model profiles.
        generation_result = await draft_pack_generator.generate_draft_pack(
            prompt=prepared_prompt,
        )

        candidate = _validate_draft_pack_candidate(
            candidate=generation_result.candidate,
            fragment_contents={str(fragment.id): fragment.contenu for fragment in fragments},
            famille_codes={taxonomy.famille_code for taxonomy in taxonomies},
        )

        return await self._repository.replace_draft_pack(
            source_id=payload.source_id,
            candidate=candidate,
            metadata=generation_result.metadata,
        )

    async def promote_pack(self, draft_pack_id: str) -> str:
        return await self._repository.promote_pack(draft_pack_id)

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
    fragment_contents: Mapping[str, str],
    famille_codes: set[str],
) -> DraftStylePackExtractionV1:
    validated_rules: list[DraftStyleRuleV1] = []
    seen_rules: dict[tuple[str, str | None, str], NiveauContrainte] = {}

    for rule in candidate.regles:
        normalized_rule = _normalize_and_validate_rule(
            rule=rule,
            fragment_contents=fragment_contents,
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


def _normalize_and_validate_rule(
    *,
    rule: DraftStyleRuleV1,
    fragment_contents: Mapping[str, str],
    famille_codes: set[str],
) -> DraftStyleRuleV1:
    fragment_content = fragment_contents.get(rule.fragment_source_id)

    if fragment_content is None:
        raise ValueError(f"fragment_source_id inconnu: {rule.fragment_source_id}")

    citation_source = _normalize_required_text(rule.citation_source, "citation_source")

    if _normalize_for_evidence(citation_source) not in _normalize_for_evidence(fragment_content):
        raise ValueError("citation_source introuvable dans le fragment reference.")

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
