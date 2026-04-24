import uuid
from typing import Protocol

from pydantic import BaseModel, Field


class StyleGuideIngestionInput(BaseModel):
    collection_id: uuid.UUID = Field(..., description="UUID du dossier style guide en base")
    document_source_id: uuid.UUID = Field(..., description="UUID du document source en base")
    ingestion_run_id: uuid.UUID = Field(..., description="UUID du run d'ingestion en base")
    storage_uri: str = Field(..., description="URI GCS du PDF du guide de style")


class StyleGuideWorkflowStarterPort(Protocol):
    async def start_style_guide_ingestion(self, payload: StyleGuideIngestionInput) -> str: ...
