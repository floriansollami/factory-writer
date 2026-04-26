from factory_writer.application.ports.product_technical_ingestion.document_processor import (
    TechnicalExtractorRoute,
)
from factory_writer.core.config import Settings
from factory_writer.domain.document_ingestion_types import DocumentType

_TECHNICAL_SHEET_EXTRACTOR_NAME = "fw-technical-sheet-extractor"
_MATERIAL_SPECIFICATION_EXTRACTOR_NAME = "fw-material-spec-extractor"
_ASSEMBLY_NOTICE_EXTRACTOR_NAME = "fw-assembly-notice-extractor"
_LEGACY_EXTRACTOR_NAME = "legacy-technical-facts-extractor"


class ConfiguredTechnicalExtractorRouter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def route_for_document_type(self, document_type: str) -> TechnicalExtractorRoute:
        gcp = self._settings.gcp

        if document_type == DocumentType.TECHNICAL_SHEET.value:
            return _specialized_or_legacy_route(
                document_type=document_type,
                extractor_name=_TECHNICAL_SHEET_EXTRACTOR_NAME,
                processor_id=gcp.document_ai_technical_sheet_extractor_processor_id,
                processor_version=gcp.document_ai_technical_sheet_extractor_processor_version,
                legacy_processor_id=gcp.document_ai_extractor_processor_id,
                legacy_processor_version=gcp.document_ai_extractor_processor_version,
                env_name="GCP__DOCUMENT_AI_TECHNICAL_SHEET_EXTRACTOR_PROCESSOR_ID",
            )

        if document_type == DocumentType.MATERIAL_SPECIFICATION.value:
            return _specialized_or_legacy_route(
                document_type=document_type,
                extractor_name=_MATERIAL_SPECIFICATION_EXTRACTOR_NAME,
                processor_id=gcp.document_ai_material_specification_extractor_processor_id,
                processor_version=gcp.document_ai_material_specification_extractor_processor_version,
                legacy_processor_id=gcp.document_ai_extractor_processor_id,
                legacy_processor_version=gcp.document_ai_extractor_processor_version,
                env_name="GCP__DOCUMENT_AI_MATERIAL_SPECIFICATION_EXTRACTOR_PROCESSOR_ID",
            )

        if document_type == DocumentType.ASSEMBLY_NOTICE.value:
            return _specialized_or_legacy_route(
                document_type=document_type,
                extractor_name=_ASSEMBLY_NOTICE_EXTRACTOR_NAME,
                processor_id=gcp.document_ai_assembly_notice_extractor_processor_id,
                processor_version=gcp.document_ai_assembly_notice_extractor_processor_version,
                legacy_processor_id=gcp.document_ai_extractor_processor_id,
                legacy_processor_version=gcp.document_ai_extractor_processor_version,
                env_name="GCP__DOCUMENT_AI_ASSEMBLY_NOTICE_EXTRACTOR_PROCESSOR_ID",
            )

        raise ValueError(f"Aucun Custom Extractor routable pour document_type={document_type}.")


def _specialized_or_legacy_route(
    *,
    document_type: str,
    extractor_name: str,
    processor_id: str,
    processor_version: str | None,
    legacy_processor_id: str,
    legacy_processor_version: str | None,
    env_name: str,
) -> TechnicalExtractorRoute:
    if processor_id:
        return TechnicalExtractorRoute(
            document_type=document_type,
            processor_id=processor_id,
            processor_version=processor_version,
            extractor_name=extractor_name,
        )

    if legacy_processor_id:
        return TechnicalExtractorRoute(
            document_type=document_type,
            processor_id=legacy_processor_id,
            processor_version=legacy_processor_version,
            extractor_name=_LEGACY_EXTRACTOR_NAME,
        )

    raise ValueError(f"{env_name} est requis pour extraire document_type={document_type}.")
