import pytest

from factory_writer.application.services.technical_extractor_router import (
    ConfiguredTechnicalExtractorRouter,
)
from factory_writer.core.config import GCPSettings, Settings


@pytest.mark.parametrize(
    ("document_type", "processor_id", "extractor_name"),
    [
        ("TECHNICAL_SHEET", "51d79fcf170d4db5", "fw-technical-sheet-extractor"),
        ("MATERIAL_SPECIFICATION", "6a06ee761cf984a5", "fw-material-spec-extractor"),
        ("ASSEMBLY_NOTICE", "e4c1655a493f899e", "fw-assembly-notice-extractor"),
    ],
)
def test_router_routes_supported_document_types(
    document_type: str,
    processor_id: str,
    extractor_name: str,
) -> None:
    router = ConfiguredTechnicalExtractorRouter(
        Settings(
            gcp=GCPSettings(
                document_ai_technical_sheet_extractor_processor_id="51d79fcf170d4db5",
                document_ai_material_specification_extractor_processor_id="6a06ee761cf984a5",
                document_ai_assembly_notice_extractor_processor_id="e4c1655a493f899e",
            )
        )
    )

    route = router.route_for_document_type(document_type)

    assert route.document_type == document_type
    assert route.processor_id == processor_id
    assert route.processor_version is None
    assert route.extractor_name == extractor_name


@pytest.mark.parametrize(
    "document_type",
    ["OUT_OF_SCOPE_DOCUMENT", "MIXED_TECHNICAL_DOSSIER", "UNKNOWN"],
)
def test_router_rejects_non_routable_document_types(document_type: str) -> None:
    router = ConfiguredTechnicalExtractorRouter(Settings())

    with pytest.raises(ValueError, match="Aucun Custom Extractor routable"):
        router.route_for_document_type(document_type)


def test_router_uses_legacy_extractor_as_fallback() -> None:
    router = ConfiguredTechnicalExtractorRouter(
        Settings(
            gcp=GCPSettings(
                document_ai_extractor_processor_id="legacy-extractor",
                document_ai_extractor_processor_version="legacy-v1",
            )
        )
    )

    route = router.route_for_document_type("TECHNICAL_SHEET")

    assert route.document_type == "TECHNICAL_SHEET"
    assert route.processor_id == "legacy-extractor"
    assert route.processor_version == "legacy-v1"
    assert route.extractor_name == "legacy-technical-facts-extractor"
