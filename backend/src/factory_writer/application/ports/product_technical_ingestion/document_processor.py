from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TechnicalExtractorRoute:
    document_type: str
    processor_id: str
    processor_version: str | None
    extractor_name: str


class TechnicalExtractorRouterPort(Protocol):
    def route_for_document_type(self, document_type: str) -> TechnicalExtractorRoute: ...


@dataclass(frozen=True)
class TechnicalDocumentClassificationResult:
    processor_resource_name: str
    processor_version: str | None
    document_type: str
    confidence: float | None
    latency_ms: int
    request_config_snapshot: dict[str, Any]
    raw_response_summary: dict[str, Any]


@dataclass(frozen=True)
class TechnicalDocumentEntity:
    field_name: str
    raw_value: str | None
    confidence: float | None
    page: int | None
    bbox_json: dict[str, Any] | None


@dataclass(frozen=True)
class TechnicalDocumentExtractionResult:
    processor_resource_name: str
    processor_version: str | None
    latency_ms: int
    request_config_snapshot: dict[str, Any]
    entities: list[TechnicalDocumentEntity]


class TechnicalDocumentProcessorPort(Protocol):
    async def classify_technical_document(
        self,
        *,
        input_uri: str,
        mime_type: str = "application/pdf",
    ) -> TechnicalDocumentClassificationResult: ...

    async def extract_technical_facts(
        self,
        *,
        input_uri: str,
        document_type: str,
        extractor_route: TechnicalExtractorRoute,
        mime_type: str = "application/pdf",
    ) -> TechnicalDocumentExtractionResult: ...
