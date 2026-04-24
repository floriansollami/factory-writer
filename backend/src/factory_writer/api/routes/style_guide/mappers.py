from factory_writer.application.services.style_guide_admin_service import (
    StyleGuideOverviewActivePack,
    StyleGuideOverviewPendingDocumentSource,
    StyleGuideOverviewRecentPack,
    StyleGuideOverviewResult,
    StyleGuideOverviewRule,
    StyleGuideOverviewWorkflow,
)
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideUploadResult,
)


def to_upload_response(
    result: StyleGuideUploadResult,
    file_name: str,
) -> dict[str, str]:
    return {
        "status": result.status.value,
        "documentSourceId": str(result.document_source_id),
        "storageUri": result.storage_uri,
        "fileName": file_name,
        "storageGeneration": result.storage_generation,
        "storageMetageneration": result.storage_metageneration,
        "createdAt": result.created_at.isoformat(),
        "updatedAt": result.updated_at.isoformat(),
    }


def to_overview_response(overview: StyleGuideOverviewResult) -> dict[str, object]:
    return {
        "activePack": (
            _to_active_pack_response(overview.active_pack)
            if overview.active_pack is not None
            else None
        ),
        "pendingDocumentSource": (
            _to_pending_document_source_response(overview.pending_document_source)
            if overview.pending_document_source is not None
            else None
        ),
        "currentWorkflow": (
            _to_current_workflow_response(overview.current_workflow)
            if overview.current_workflow is not None
            else None
        ),
        "metrics": {
            "activeRules": overview.metrics.active_rules,
            "needsReview": overview.metrics.needs_review,
            "disabledRules": overview.metrics.disabled_rules,
            "missingProvenance": overview.metrics.missing_provenance,
        },
        "rules": [_to_rule_response(rule) for rule in overview.rules],
        "recentPacks": [_to_recent_pack_response(pack) for pack in overview.recent_packs],
    }


def _to_active_pack_response(pack: StyleGuideOverviewActivePack) -> dict[str, object]:
    return {
        "id": str(pack.style_pack_id),
        "version": pack.version,
        "status": pack.status,
        "documentSourcePdf": pack.document_source_pdf,
        "approvedBy": pack.approved_by,
        "approvedAt": pack.approved_at.isoformat() if pack.approved_at is not None else None,
        "rulesCount": pack.rules_count,
        "hardRulesCount": pack.hard_rules_count,
        "softRulesCount": pack.soft_rules_count,
        "scopes": pack.scopes,
    }


def _to_pending_document_source_response(
    document_source: StyleGuideOverviewPendingDocumentSource,
) -> dict[str, object]:
    return {
        "documentSourceId": str(document_source.document_source_id),
        "fileName": document_source.file_name,
        "status": document_source.status,
        "storageUri": document_source.storage_uri,
        "storageGeneration": document_source.storage_generation,
        "storageMetageneration": document_source.storage_metageneration,
        "uploadedAt": document_source.uploaded_at.isoformat(),
        "updatedAt": document_source.updated_at.isoformat(),
    }


def _to_current_workflow_response(workflow_result: StyleGuideOverviewWorkflow) -> dict[str, object]:
    return {
        "workflowId": workflow_result.workflow_id,
        "documentSourceId": str(workflow_result.document_source_id),
        "ingestionRunId": str(workflow_result.ingestion_run_id),
        "status": workflow_result.status,
        "currentActivity": workflow_result.current_activity,
        "elapsedTime": workflow_result.elapsed_time,
        "progress": workflow_result.progress,
        "steps": [
            {
                "id": step.id,
                "label": step.label,
                "description": step.description,
                "status": step.status,
                **({"eta": step.eta} if step.eta is not None else {}),
            }
            for step in workflow_result.steps
        ],
    }


def _to_rule_response(rule: StyleGuideOverviewRule) -> dict[str, object]:
    return {
        "id": str(rule.id),
        "typeRegle": rule.type_regle,
        "niveauContrainte": rule.niveau_contrainte,
        "texteRegle": rule.texte_regle,
        "taxonomieCode": rule.taxonomie_code,
        "estActif": rule.est_actif,
        "decisionEditoriale": rule.decision_editoriale,
        "origine": rule.origine,
        "provenance": {
            "providerId": rule.provenance.provider_id,
            "indexChunk": rule.provenance.index_chunk,
            "extrait": rule.provenance.extrait,
            "pageStart": rule.provenance.page_start,
            "pageEnd": rule.provenance.page_end,
            "metadata": rule.provenance.metadata,
        },
        "review": {
            "commentaire": rule.review.commentaire,
            "reviewedAt": (
                rule.review.reviewed_at.isoformat() if rule.review.reviewed_at is not None else None
            ),
            "reviewedBy": rule.review.reviewed_by,
        },
        "runtime": {
            "packIsActive": rule.runtime.pack_is_active,
            "ruleIsActive": rule.runtime.rule_is_active,
        },
    }


def _to_recent_pack_response(pack: StyleGuideOverviewRecentPack) -> dict[str, object]:
    return {
        "version": pack.version,
        "documentSourcePdf": pack.document_source_pdf,
        "status": pack.status,
        "rulesCount": pack.rules_count,
        "approvedRulesCount": pack.approved_rules_count,
        "disabledRulesCount": pack.disabled_rules_count,
        "approvedBy": pack.approved_by,
        "updatedAt": pack.updated_at.isoformat(),
    }
