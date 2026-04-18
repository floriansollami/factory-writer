import uuid
from typing import Protocol

from pydantic import BaseModel, Field


class StyleGuideIngestionInput(BaseModel):
    source_id: uuid.UUID = Field(..., description="UUID du document source en base")
    file_uri: str = Field(..., description="URI GCS du PDF du style guide")


class StyleGuideWorkflowStarterPort(Protocol):
    async def start_style_guide_ingestion(self, payload: StyleGuideIngestionInput) -> str: ...
