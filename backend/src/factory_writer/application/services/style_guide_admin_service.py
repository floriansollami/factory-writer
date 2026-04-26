from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from factory_writer.application.ports.style_guide_ingestion import (
    StyleGuideDocumentSourceSnapshot,
    StyleGuideIngestionRunSnapshot,
    StyleGuidePackSnapshot,
    StyleGuideRepositoryPort,
    StyleGuideRuleSnapshot,
    StyleGuideWorkflowControllerPort,
)
from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    DecisionEditorialeStyleRule,
    StatutDocumentIngestionRun,
    StatutStylePack,
)
from factory_writer.domain.style_guide_types import NiveauContrainte, StatutSource, TypeRegle

_REVIEWER_NAME = "Sophie"


@dataclass(frozen=True)
class StyleGuideOverviewMetadataField:
    label: str
    value: str


@dataclass(frozen=True)
class StyleGuideOverviewExecutionMetadata:
    document_ai: list[StyleGuideOverviewMetadataField]
    llm: list[StyleGuideOverviewMetadataField]


@dataclass(frozen=True)
class StyleGuideOverviewPendingDocumentSource:
    document_source_id: uuid.UUID
    file_name: str
    status: str
    storage_uri: str
    storage_generation: str | None
    storage_metageneration: str | None
    uploaded_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class StyleGuideOverviewWorkflowStep:
    id: str
    label: str
    description: str
    status: str
    eta: str | None = None


@dataclass(frozen=True)
class StyleGuideOverviewWorkflow:
    workflow_id: str
    document_source_id: uuid.UUID
    ingestion_run_id: uuid.UUID
    status: str
    current_activity: str
    elapsed_time: str
    progress: int
    steps: list[StyleGuideOverviewWorkflowStep]
    metadata: StyleGuideOverviewExecutionMetadata


@dataclass(frozen=True)
class StyleGuideOverviewActivePack:
    style_pack_id: uuid.UUID
    version: str
    status: str
    document_source_pdf: str
    approved_by: str | None
    approved_at: datetime | None
    rules_count: int
    hard_rules_count: int
    soft_rules_count: int
    scopes: list[str]
    metadata: StyleGuideOverviewExecutionMetadata


@dataclass(frozen=True)
class StyleGuideOverviewMetrics:
    active_rules: int
    needs_review: int
    disabled_rules: int
    missing_provenance: int


@dataclass(frozen=True)
class StyleGuideOverviewRuleProvenance:
    provider_id: str | None
    index_chunk: int | None
    extrait: str
    page_start: int | None
    page_end: int | None
    metadata: object | None


@dataclass(frozen=True)
class StyleGuideOverviewRuleReview:
    commentaire: str | None
    reviewed_at: datetime | None
    reviewed_by: str | None


@dataclass(frozen=True)
class StyleGuideOverviewRuleRuntime:
    pack_is_active: bool
    rule_is_active: bool


@dataclass(frozen=True)
class StyleGuideOverviewRule:
    id: uuid.UUID
    type_regle: str
    niveau_contrainte: str
    texte_regle: str
    taxonomie_code: str | None
    est_actif: bool
    decision_editoriale: str
    origine: str
    provenance: StyleGuideOverviewRuleProvenance
    review: StyleGuideOverviewRuleReview
    runtime: StyleGuideOverviewRuleRuntime


@dataclass(frozen=True)
class StyleGuideOverviewRecentPack:
    version: str
    document_source_pdf: str
    status: str
    rules_count: int
    approved_rules_count: int
    disabled_rules_count: int
    approved_by: str | None
    updated_at: datetime


@dataclass(frozen=True)
class StyleGuideOverviewResult:
    active_pack: StyleGuideOverviewActivePack | None
    pending_document_source: StyleGuideOverviewPendingDocumentSource | None
    current_workflow: StyleGuideOverviewWorkflow | None
    metrics: StyleGuideOverviewMetrics
    rules: list[StyleGuideOverviewRule]
    recent_packs: list[StyleGuideOverviewRecentPack]


class StyleGuideAdminService:
    def __init__(
        self,
        repository: StyleGuideRepositoryPort,
        *,
        workflow_controller: StyleGuideWorkflowControllerPort | None = None,
    ) -> None:
        self._repository = repository
        self._workflow_controller = workflow_controller

    async def get_overview(self) -> StyleGuideOverviewResult:
        current_document_source = await self._repository.get_current_document_source()
        latest_run = None
        if current_document_source is not None:
            latest_run = await self._repository.get_latest_ingestion_run_for_document_source(
                current_document_source.id
            )

        all_recent_pack_snapshots = await self._repository.list_recent_packs(limit=20)
        current_collection_pack_snapshots = _filter_recent_packs_for_current_collection(
            all_recent_pack_snapshots,
            current_document_source,
        )
        draft_pack = next(
            (
                pack
                for pack in current_collection_pack_snapshots
                if pack.statut == StatutStylePack.BROUILLON
            ),
            None,
        )
        active_pack = next(
            (
                pack
                for pack in current_collection_pack_snapshots
                if pack.statut == StatutStylePack.ACTIF
            ),
            None,
        )
        selected_pack = (
            draft_pack
            or active_pack
            or (current_collection_pack_snapshots[0] if current_collection_pack_snapshots else None)
        )
        rules = (
            await self._repository.list_rules_for_pack(selected_pack.id)
            if selected_pack is not None
            else []
        )

        current_workflow = _build_current_workflow(
            current_document_source,
            latest_run,
        )
        pending_document_source = _build_pending_document_source(
            current_document_source,
            latest_run,
            draft_pack,
        )
        recent_packs = [_to_recent_pack(pack) for pack in all_recent_pack_snapshots[:5]]

        return StyleGuideOverviewResult(
            active_pack=_to_active_pack(selected_pack) if selected_pack is not None else None,
            pending_document_source=pending_document_source,
            current_workflow=current_workflow,
            metrics=_build_metrics(rules),
            rules=[
                _to_overview_rule(
                    rule,
                    pack_is_active=selected_pack.est_actif if selected_pack is not None else False,
                )
                for rule in rules
            ],
            recent_packs=recent_packs,
        )

    async def patch_rule(
        self,
        *,
        style_pack_id: uuid.UUID,
        rule_id: uuid.UUID,
        texte_regle: str | None = None,
        type_regle: TypeRegle | None = None,
        niveau_contrainte: NiveauContrainte | None = None,
        taxonomie_code: str | None = None,
        decision_editoriale: DecisionEditorialeStyleRule | None = None,
        est_actif: bool | None = None,
        commentaire_review: str | None = None,
    ) -> StyleGuideRuleSnapshot:
        return await self._repository.update_style_rule(
            style_pack_id=style_pack_id,
            rule_id=rule_id,
            texte_regle=texte_regle,
            type_regle=type_regle,
            niveau_contrainte=niveau_contrainte,
            taxonomie_code=taxonomie_code,
            decision_editoriale=decision_editoriale,
            est_actif=est_actif,
            commentaire_review=commentaire_review,
            reviewed_by=_REVIEWER_NAME,
        )

    async def approve_style_pack(self, *, style_pack_id: uuid.UUID) -> None:
        workflow_controller = self._require_workflow_controller()
        pack = await self._repository.get_pack_by_id(style_pack_id)
        if pack is None:
            raise KeyError(str(style_pack_id))
        _require_approvable_pack(pack)

        rules = await self._repository.list_rules_for_pack(style_pack_id)
        if any(rule.decision_editoriale == DecisionEditorialeStyleRule.A_VALIDER for rule in rules):
            raise RuntimeError("Toutes les règles doivent recevoir une décision avant activation.")

        await workflow_controller.approve_style_pack(
            workflow_id=pack.temporal_workflow_id,
            style_pack_id=str(pack.id),
        )

    async def reject_style_pack(self, *, style_pack_id: uuid.UUID) -> None:
        workflow_controller = self._require_workflow_controller()
        pack = await self._repository.get_pack_by_id(style_pack_id)
        if pack is None:
            raise KeyError(str(style_pack_id))
        _require_approvable_pack(pack)

        await workflow_controller.reject_style_pack(
            workflow_id=pack.temporal_workflow_id,
            style_pack_id=str(pack.id),
        )

    def _require_workflow_controller(self) -> StyleGuideWorkflowControllerPort:
        if self._workflow_controller is None:
            raise RuntimeError("workflow controller non configuré")
        return self._workflow_controller


def _build_pending_document_source(
    document_source: StyleGuideDocumentSourceSnapshot | None,
    latest_run: StyleGuideIngestionRunSnapshot | None,
    draft_pack: StyleGuidePackSnapshot | None,
) -> StyleGuideOverviewPendingDocumentSource | None:
    if document_source is None:
        return None

    if document_source.statut != StatutSource.EN_ATTENTE:
        return None

    if draft_pack is not None and draft_pack.collection_id == document_source.collection_id:
        return None

    if latest_run is not None and latest_run.statut == StatutDocumentIngestionRun.EN_COURS:
        return None

    return StyleGuideOverviewPendingDocumentSource(
        document_source_id=document_source.id,
        file_name=document_source.original_file_name,
        status=document_source.statut.value,
        storage_uri=document_source.storage_uri,
        storage_generation=document_source.storage_generation,
        storage_metageneration=document_source.storage_metageneration,
        uploaded_at=_require_datetime(document_source.created_at, "created_at"),
        updated_at=_require_datetime(document_source.updated_at, "updated_at"),
    )


def _filter_recent_packs_for_current_collection(
    packs: list[StyleGuidePackSnapshot],
    document_source: StyleGuideDocumentSourceSnapshot | None,
) -> list[StyleGuidePackSnapshot]:
    if document_source is None:
        return packs

    return [pack for pack in packs if pack.collection_id == document_source.collection_id]


def _build_current_workflow(
    document_source: StyleGuideDocumentSourceSnapshot | None,
    latest_run: StyleGuideIngestionRunSnapshot | None,
) -> StyleGuideOverviewWorkflow | None:
    if (
        document_source is None
        or latest_run is None
        or latest_run.statut != StatutDocumentIngestionRun.EN_COURS
    ):
        return None

    step_started_at = latest_run.updated_at or latest_run.started_at
    step_started_at = _require_datetime(step_started_at, "step_started_at")
    elapsed_seconds = max(1, int((datetime.now(UTC) - step_started_at).total_seconds()))
    progress, current_activity, steps = _build_workflow_progress(latest_run.current_step)

    return StyleGuideOverviewWorkflow(
        workflow_id=latest_run.temporal_workflow_id,
        document_source_id=document_source.id,
        ingestion_run_id=latest_run.id,
        status="RUNNING",
        current_activity=current_activity,
        elapsed_time=_format_elapsed_time(elapsed_seconds),
        progress=progress,
        steps=steps,
        metadata=_build_execution_metadata(
            extraction_steps_json=latest_run.extraction_steps_json,
            pack=None,
        ),
    )


def _format_elapsed_time(elapsed_seconds: int) -> str:
    if elapsed_seconds < 60:
        return f"{elapsed_seconds} s"

    if elapsed_seconds < 3600:
        minutes, seconds = divmod(elapsed_seconds, 60)
        if seconds == 0:
            return f"{minutes} min"
        return f"{minutes} min {seconds:02d} s"

    hours, remaining_seconds = divmod(elapsed_seconds, 3600)
    minutes = remaining_seconds // 60
    if minutes == 0:
        return f"{hours} h"
    return f"{hours} h {minutes:02d} min"


def _build_workflow_progress(
    current_step: CurrentStep,
) -> tuple[int, str, list[StyleGuideOverviewWorkflowStep]]:
    document_ai_done = current_step in (CurrentStep.LLM_DRAFT_PACK, CurrentStep.HUMAN_REVIEW)
    draft_pack_running = current_step == CurrentStep.LLM_DRAFT_PACK

    return (
        72 if document_ai_done else 35,
        "Préparation du pack candidat" if document_ai_done else "Extraction du contenu",
        [
            StyleGuideOverviewWorkflowStep(
                id="document-ai",
                label="Extraction du contenu",
                description="Le contenu du PDF est analysé et structuré pour préparer les règles.",
                status="completed" if document_ai_done else "running",
                eta=None if document_ai_done else "souvent 1 min",
            ),
            StyleGuideOverviewWorkflowStep(
                id="draft-pack",
                label="Pack candidat",
                description="Les règles de voix, de ton et de formulation sont préparées pour la revue.",
                status="running"
                if draft_pack_running
                else ("completed" if current_step == CurrentStep.HUMAN_REVIEW else "pending"),
                eta=None if current_step == CurrentStep.HUMAN_REVIEW else "souvent 15 secondes",
            ),
            StyleGuideOverviewWorkflowStep(
                id="editorial-review",
                label="Revue éditoriale",
                description="Les règles proposées sont relues, corrigées ou approuvées.",
                status="completed" if current_step == CurrentStep.HUMAN_REVIEW else "pending",
            ),
        ],
    )


def _build_execution_metadata(
    *,
    extraction_steps_json: Any | None,
    pack: StyleGuidePackSnapshot | None,
) -> StyleGuideOverviewExecutionMetadata:
    steps = _normalize_extraction_steps(extraction_steps_json)
    document_ai_step = next(
        (step for step in steps if step.get("step_kind") in {"LAYOUT_PARSE", "OCR_PROOF"}),
        None,
    )
    llm_step = next(
        (step for step in steps if step.get("step_kind") == "LLM_DRAFT_PACK"),
        None,
    )

    return StyleGuideOverviewExecutionMetadata(
        document_ai=_build_document_ai_metadata(document_ai_step),
        llm=_build_llm_metadata(llm_step, pack),
    )


def _normalize_extraction_steps(extraction_steps_json: Any | None) -> list[dict[str, Any]]:
    if isinstance(extraction_steps_json, list):
        return [step for step in extraction_steps_json if isinstance(step, dict)]

    if isinstance(extraction_steps_json, dict):
        steps = extraction_steps_json.get("steps")
        if isinstance(steps, list):
            return [step for step in steps if isinstance(step, dict)]

    return []


def _build_document_ai_metadata(
    step: dict[str, Any] | None,
) -> list[StyleGuideOverviewMetadataField]:
    if step is None:
        return []

    processor_resource_name = _optional_string(step.get("processor_resource_name"))

    return _compact_metadata_fields(
        [
            ("Fournisseur", "Google Document AI"),
            (
                "Processor",
                _processor_id_from_resource_name(processor_resource_name)
                or _optional_string(step.get("processor_kind")),
            ),
            ("Version", _document_ai_processor_version_label(step.get("processor_version"))),
        ]
    )


def _build_llm_metadata(
    step: dict[str, Any] | None,
    pack: StyleGuidePackSnapshot | None,
) -> list[StyleGuideOverviewMetadataField]:
    if step is None and pack is None:
        return []

    return _compact_metadata_fields(
        [
            ("Fournisseur", "LiteLLM"),
            ("Modèle", _metadata_value(step, "llm_model", pack.llm_model if pack else None)),
            (
                "Température",
                _metadata_value(step, "llm_temperature", pack.llm_temperature if pack else None),
            ),
            (
                "Max tokens",
                _metadata_value(step, "llm_max_tokens", pack.llm_max_tokens if pack else None),
            ),
            (
                "Version",
                _metadata_value(step, "prompt_version", pack.prompt_version if pack else None),
            ),
        ]
    )


def _metadata_value(
    step: dict[str, Any] | None,
    key: str,
    fallback: object | None = None,
) -> str | None:
    if step is not None and key in step:
        return _optional_string(step.get(key))
    return _optional_string(fallback)


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _document_ai_processor_version_label(value: object | None) -> str | None:
    version = _optional_string(value)
    if version == "pretrained-layout-parser-v1.6-2026-01-13":
        return f"{version} (Gemini 3.0 Flash)"
    return version


def _processor_id_from_resource_name(resource_name: str | None) -> str | None:
    if resource_name is None:
        return None

    parts = PurePosixPath(resource_name).parts
    try:
        processor_index = parts.index("processors")
        return parts[processor_index + 1]
    except (ValueError, IndexError):
        return None


def _compact_metadata_fields(
    pairs: list[tuple[str, str | None]],
) -> list[StyleGuideOverviewMetadataField]:
    return [
        StyleGuideOverviewMetadataField(label=label, value=value)
        for label, value in pairs
        if value is not None
    ]


def _to_active_pack(pack: StyleGuidePackSnapshot) -> StyleGuideOverviewActivePack:
    return StyleGuideOverviewActivePack(
        style_pack_id=pack.id,
        version=str(pack.id),
        status=pack.statut.value,
        document_source_pdf=pack.original_file_name,
        approved_by=_REVIEWER_NAME if pack.approuve_le is not None else None,
        approved_at=pack.approuve_le,
        rules_count=pack.rules_count,
        hard_rules_count=pack.hard_rules_count,
        soft_rules_count=pack.soft_rules_count,
        scopes=pack.scopes,
        metadata=_build_execution_metadata(
            extraction_steps_json=pack.extraction_steps_json,
            pack=pack,
        ),
    )


def _build_metrics(rules: list[StyleGuideRuleSnapshot]) -> StyleGuideOverviewMetrics:
    return StyleGuideOverviewMetrics(
        active_rules=sum(
            1 for rule in rules if rule.decision_editoriale == DecisionEditorialeStyleRule.APPROUVEE
        ),
        needs_review=sum(
            1 for rule in rules if rule.decision_editoriale == DecisionEditorialeStyleRule.A_VALIDER
        ),
        disabled_rules=sum(
            1
            for rule in rules
            if rule.decision_editoriale == DecisionEditorialeStyleRule.DESACTIVEE
        ),
        missing_provenance=sum(1 for rule in rules if not rule.source_evidence_provider_id),
    )


def _to_overview_rule(
    rule: StyleGuideRuleSnapshot,
    *,
    pack_is_active: bool,
) -> StyleGuideOverviewRule:
    index_chunk = None
    if isinstance(rule.source_evidence_json, dict):
        raw_index_chunk = rule.source_evidence_json.get("index_chunk")
        index_chunk = raw_index_chunk if isinstance(raw_index_chunk, int) else None

    return StyleGuideOverviewRule(
        id=rule.id,
        type_regle=rule.type_regle.value,
        niveau_contrainte=rule.niveau_contrainte.value,
        texte_regle=rule.texte_regle,
        taxonomie_code=rule.taxonomie_code,
        est_actif=rule.est_actif,
        decision_editoriale=rule.decision_editoriale.value,
        origine=_map_rule_origin(rule.origine.value),
        provenance=StyleGuideOverviewRuleProvenance(
            provider_id=rule.source_evidence_provider_id,
            index_chunk=index_chunk,
            extrait=rule.source_evidence_text or "",
            page_start=rule.source_evidence_page_start,
            page_end=rule.source_evidence_page_end,
            metadata=rule.source_evidence_json,
        ),
        review=StyleGuideOverviewRuleReview(
            commentaire=rule.commentaire_review,
            reviewed_at=rule.reviewed_at,
            reviewed_by=rule.reviewed_by,
        ),
        runtime=StyleGuideOverviewRuleRuntime(
            pack_is_active=pack_is_active,
            rule_is_active=rule.est_actif,
        ),
    )


def _to_recent_pack(pack: StyleGuidePackSnapshot) -> StyleGuideOverviewRecentPack:
    return StyleGuideOverviewRecentPack(
        version=str(pack.id),
        document_source_pdf=pack.original_file_name,
        status=pack.statut.value,
        rules_count=pack.rules_count,
        approved_rules_count=pack.approved_rules_count,
        disabled_rules_count=pack.disabled_rules_count,
        approved_by=_REVIEWER_NAME if pack.approuve_le is not None else None,
        updated_at=_require_datetime(pack.updated_at, "updated_at"),
    )


def _map_rule_origin(origin: str) -> str:
    if origin == "LLM":
        return "IA"
    if origin == "HUMAIN":
        return "MODIFIEE"
    return origin


def _require_approvable_pack(pack: StyleGuidePackSnapshot) -> None:
    if pack.statut != StatutStylePack.BROUILLON:
        raise RuntimeError("Seul un pack brouillon peut recevoir une décision finale.")
    if pack.run_statut != StatutDocumentIngestionRun.A_VALIDER:
        raise RuntimeError("Ce pack n'est plus en attente de validation humaine.")


def _require_datetime(value: datetime | None, field_name: str) -> datetime:
    if value is None:
        raise RuntimeError(f"{field_name} manquant.")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
