from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from factory_writer.domain.style_guide_types import StatutSource
from factory_writer.temporal.style_guide_ingestion.contracts import StyleGuideIngestionInput


@dataclass(frozen=True)
class GcsObjectMetadata:
    bucket_name: str
    object_name: str
    generation: str
    metageneration: str


@dataclass(frozen=True)
class DocumentAIProcessResult:
    processor_resource_name: str
    operation_id: str
    output_uri: str


class StyleGuideStartStatus(StrEnum):
    STARTED = "started"
    IGNORED = "ignored"


@dataclass(frozen=True)
class StyleGuideSourceSnapshot:
    id: uuid.UUID
    uri_fichier: str
    statut: StatutSource
    generation_gcs: str | None = None
    operation_docai_id: str | None = None
    uri_sortie_docai: str | None = None


@dataclass(frozen=True)
class StyleGuideIngestionStartResult:
    status: StyleGuideStartStatus
    reason: str | None = None
    source_id: str | None = None
    workflow_id: str | None = None


class StyleGuideRepositoryPort(Protocol):
    async def get_by_uri(self, uri: str) -> StyleGuideSourceSnapshot | None: ...

    async def create_source(
        self,
        uri: str,
        statut: StatutSource,
    ) -> StyleGuideSourceSnapshot: ...

    async def update_source_status(
        self,
        source_id: uuid.UUID,
        statut: StatutSource,
        error_message: str | None = None,
        only_if_not_terminal: bool = False,
    ) -> StyleGuideSourceSnapshot: ...

    async def update_gcs_metadata(
        self,
        source_id: uuid.UUID,
        bucket_name: str,
        object_name: str,
        generation: str,
        metageneration: str,
    ) -> StyleGuideSourceSnapshot: ...

    async def update_docai_output(
        self,
        source_id: uuid.UUID,
        docai_resource: str,
        operation_id: str,
        output_uri: str,
        error_message: str | None = None,
    ) -> StyleGuideSourceSnapshot: ...

    async def update_error_message(self, source_id: uuid.UUID, message: str) -> None: ...


class StyleGuideStoragePort(Protocol):
    async def get_blob_metadata(self, bucket_name: str, object_name: str) -> GcsObjectMetadata | None: ...

    async def has_blobs_with_prefix(self, bucket_name: str, prefix: str) -> bool: ...


class StyleGuideDocumentParserPort(Protocol):
    async def process_document_lro(
        self,
        input_uri: str,
        output_uri: str,
        heartbeat_callback: Callable[[dict[str, str]], None] | None = None,
    ) -> DocumentAIProcessResult: ...


class StyleGuideWorkflowStarterPort(Protocol):
    async def start_style_guide_ingestion(self, payload: StyleGuideIngestionInput) -> str: ...
