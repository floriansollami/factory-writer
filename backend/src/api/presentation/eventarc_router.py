from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.application.use_cases.ingest_style_guide import trigger_style_ingestion
from api.domain.schemas.cloud_event import StorageObjectData
from api.infrastructure.database.session import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/style-guide", status_code=200)
async def handle_style_guide_eventarc(
    request: Request,
    payload: StorageObjectData,
    ce_type: str = Header(
        None,
        description="Type d'évènement CloudEvent (ex: google.cloud.storage.object.v1.finalized)",
    ),
    ce_id: str = Header(None, description="Identifiant unique de CloudEvent"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Webhook d'entrée appelé par Google Eventarc.
    Strictement lié à l'API Eventarc: Pydantic filtre et valide le JSON Payload de Storage.
    """
    logger.info(
        "Webhook Triggered : Réception d'un CloudEvent HTTP.",
        ce_id=ce_id,
        ce_type=ce_type,
        bucket=payload.bucket,
        file_name=payload.name,
    )

    if not ce_type:
        logger.warning("Événement rejeté : Entête 'ce-type' manquant.")
        raise HTTPException(
            status_code=400, detail="Ce webhook n'accepte que des standards CloudEvents GCP."
        )

    # Google Storage génère ce `ce_type` à chaque fin d'upload réussi.
    if ce_type != "google.cloud.storage.object.v1.finalized":
        logger.warning(
            "Événement ignoré car non pertinent.", ce_type=ce_type, message="Non-finalized event."
        )
        return {"msg": "Ignored: not a finalized object upload event."}

    # Une fois la validation technique web actée, la balle passe à la couche Métier / Application.
    result = await trigger_style_ingestion(
        bucket_name=payload.bucket, file_name=payload.name, session=session
    )

    return {"status": "ok", "workflow_metadata": result}
