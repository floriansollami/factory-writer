import uuid

from fastapi import APIRouter, Depends, HTTPException

from factory_writer.api.routes.style_guide.dependencies import (
    STYLE_GUIDE_TAG,
    get_style_guide_ingestion_service,
)
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)
from factory_writer.domain.style_guide_types import StatutSource

router = APIRouter()


@router.post(
    "/document-sources/{document_source_id}/start-ingestion",
    status_code=202,
    tags=[STYLE_GUIDE_TAG],
)
async def start_style_guide_ingestion(
    document_source_id: uuid.UUID,
    service: StyleGuideIngestionService = Depends(get_style_guide_ingestion_service),
) -> dict[str, str]:
    try:
        result = await service.start_ingestion(document_source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source guide de style introuvable.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "status": StatutSource.EN_COURS.value,
        "collectionId": str(result.collection_id),
        "ingestionRunId": str(result.ingestion_run_id),
        "documentSourceId": str(result.document_source_id),
        "storageUri": result.storage_uri,
        "workflowId": result.workflow_id,
    }
