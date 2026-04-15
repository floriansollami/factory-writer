import structlog
from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from factory_writer.api.routes.schemas.eventarc_payload import StorageObjectData
from factory_writer.application.use_cases.ingest_style_guide import trigger_style_ingestion
from factory_writer.domain.exceptions import (
    NotAPdfError,
    StyleGuideAlreadyExistsError,
    WrongBucketError,
)
from factory_writer.infrastructure.database.session import get_db_session

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/style-guide", status_code=200)
async def handle_style_guide_eventarc(
    payload: StorageObjectData,
    ce_type: str = Header(
        ...,
        description="Type d'évènement CloudEvent (ex: google.cloud.storage.object.v1.finalized)",
    ),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Webhook d'entrée appelé par Google Eventarc.
    Strictement lié à l'API Eventarc: Pydantic filtre et valide le JSON Payload de Storage.
    """
    # Google Storage génère ce `ce_type` à chaque fin d'upload réussi.
    if ce_type != "google.cloud.storage.object.v1.finalized":
        return Response(status_code=200)

    # Une fois la validation technique web actée, la balle passe à la couche Métier / Application.
    try:
        await trigger_style_ingestion(
            bucket_name=payload.bucket, file_name=payload.name, session=session
        )
        return Response(status_code=200)
    except (WrongBucketError, NotAPdfError, StyleGuideAlreadyExistsError) as exc:
        logger.info(
            "Style guide event ignored",
            reason=exc.code,
            bucket=payload.bucket,
            file_name=payload.name,
        )
        return Response(status_code=200)
