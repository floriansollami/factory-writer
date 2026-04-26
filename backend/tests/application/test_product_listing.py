from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from factory_writer.api.routes.products.schemas import ProductCreateRequest
from factory_writer.application.ports.product_technical_ingestion import (
    ProductContextReference,
    ProductSnapshot,
    ProductTaxonomySnapshot,
)
from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)
from factory_writer.core.config import Settings


@pytest.mark.anyio
async def test_list_products_returns_frontend_ready_payload() -> None:
    created_at = datetime(2026, 4, 25, 9, 12, tzinfo=UTC)
    product = ProductSnapshot(
        id=uuid.UUID("7e8d7c1d-9f3a-4a89-9f1b-4f9f5b8d2a11"),
        sku="AX-TB-RIV-220-TKGR",
        name="Table Rivage 220",
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        season_code="printemps_ete",
        segment_prix_code="premium",
        langue_principale="fr-FR",
        created_at=created_at,
    )
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(Any, _FakeProductRepository(products=(product,))),
    )

    result = await service.list_products()

    assert result == {
        "products": [
            {
                "id": "7e8d7c1d-9f3a-4a89-9f1b-4f9f5b8d2a11",
                "sku": "AX-TB-RIV-220-TKGR",
                "name": "Table Rivage 220",
                "familleCode": "mobilier_jardin",
                "sousFamilleCode": "table_repas_exterieur",
                "seasonCode": "printemps_ete",
                "segmentPrixCode": "premium",
                "languePrincipale": "fr-FR",
                "readinessStatus": "PRODUCT_CREATED",
                "styleGuideReady": True,
                "commercialSignalsReady": True,
                "createdAt": "2026-04-25T09:12:00+00:00",
            }
        ]
    }


@pytest.mark.anyio
async def test_list_products_marks_missing_generation_prerequisites() -> None:
    product = ProductSnapshot(
        id=uuid.UUID("7e8d7c1d-9f3a-4a89-9f1b-4f9f5b8d2a11"),
        sku="AX-TB-RIV-220-TKGR",
        name="Table Rivage 220",
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        season_code="printemps_ete",
        segment_prix_code="premium",
        langue_principale="fr-FR",
    )
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(
            Any,
            _FakeProductRepository(
                products=(product,),
                style_guide_ready=False,
                commercial_signals_ready=False,
            ),
        ),
    )

    result = await service.list_products()

    assert result["products"][0]["styleGuideReady"] is False
    assert result["products"][0]["commercialSignalsReady"] is False


@pytest.mark.anyio
async def test_list_products_marks_uploaded_sources_as_ready_to_analyze() -> None:
    product_id = uuid.UUID("7e8d7c1d-9f3a-4a89-9f1b-4f9f5b8d2a11")
    product = ProductSnapshot(
        id=product_id,
        sku="AX-TB-RIV-220-TKGR",
        name="Table Rivage 220",
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        season_code="printemps_ete",
        segment_prix_code="premium",
        langue_principale="fr-FR",
    )
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(
            Any,
            _FakeProductRepository(
                products=(product,),
                product_overviews={
                    product_id: {
                        "sources": [{"id": "source-1"}],
                        "run": None,
                        "review_cases": [],
                        "product_context_snapshot": None,
                    }
                },
            ),
        ),
    )

    result = await service.list_products()

    assert result["products"][0]["readinessStatus"] == "TECHNICAL_SOURCES_UPLOADED"


@pytest.mark.anyio
async def test_create_product_returns_product_and_starts_lifecycle_workflow() -> None:
    product_id = uuid.UUID("7e8d7c1d-9f3a-4a89-9f1b-4f9f5b8d2a11")
    repository = _FakeProductRepository(created_product_id=product_id)
    workflow_starter = _FakeProductLifecycleWorkflowStarter()
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(Any, repository),
        workflow_starter=cast(Any, workflow_starter),
    )

    result = await service.create_product(
        sku="AX-TB-RIV-220-TKGR",
        name="Table Rivage 220",
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        season_code="printemps_ete",
        segment_prix_code="premium",
        langue_principale="fr-FR",
    )

    assert result == {
        "product": {
            "id": "7e8d7c1d-9f3a-4a89-9f1b-4f9f5b8d2a11",
            "sku": "AX-TB-RIV-220-TKGR",
            "name": "Table Rivage 220",
            "famille_code": "mobilier_jardin",
            "sous_famille_code": "table_repas_exterieur",
            "season_code": "printemps_ete",
            "segment_prix_code": "premium",
            "langue_principale": "fr-FR",
        },
        "workflow_id": "product-lifecycle-AX-TB-RIV-220-TKGR",
    }
    assert workflow_starter.started_product == ProductContextReference(
        product_id="7e8d7c1d-9f3a-4a89-9f1b-4f9f5b8d2a11",
        sku="AX-TB-RIV-220-TKGR",
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        season_code="printemps_ete",
        segment_prix_code="premium",
        langue_principale="fr-FR",
    )


def test_product_create_request_defaults_language_when_frontend_omits_it() -> None:
    payload = ProductCreateRequest.model_validate(
        {
            "sku": "AX-TB-RIV-220-TKGR",
            "name": "Table Rivage 220",
            "familleCode": "mobilier_jardin",
            "sousFamilleCode": "table_repas_exterieur",
            "seasonCode": "printemps_ete",
            "segmentPrixCode": "premium",
        }
    )

    assert payload.langue_principale == "fr-FR"


@pytest.mark.anyio
async def test_list_product_taxonomies_returns_frontend_ready_payload() -> None:
    taxonomy = ProductTaxonomySnapshot(
        id=uuid.UUID("1b42e2cf-c75f-44cb-8d1c-a9f78a29d251"),
        code="mobilier_jardin",
        libelle_fr="Mobilier de jardin",
        parent_id=None,
    )
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(Any, _FakeProductRepository(taxonomies=(taxonomy,))),
    )

    result = await service.list_product_taxonomies()

    assert result == {
        "taxonomies": [
            {
                "id": "1b42e2cf-c75f-44cb-8d1c-a9f78a29d251",
                "code": "mobilier_jardin",
                "libelleFr": "Mobilier de jardin",
                "parentId": None,
            }
        ]
    }


class _FakeProductRepository:
    def __init__(
        self,
        *,
        products: tuple[ProductSnapshot, ...] = (),
        taxonomies: tuple[ProductTaxonomySnapshot, ...] = (),
        created_product_id: uuid.UUID | None = None,
        style_guide_ready: bool = True,
        commercial_signals_ready: bool = True,
        product_overviews: dict[uuid.UUID, dict[str, Any]] | None = None,
    ) -> None:
        self._products = products
        self._taxonomies = taxonomies
        self._created_product_id = created_product_id
        self._style_guide_ready = style_guide_ready
        self._commercial_signals_ready = commercial_signals_ready
        self._product_overviews = product_overviews or {}

    async def list_products(self, *, limit: int = 50) -> tuple[ProductSnapshot, ...]:
        return self._products[:limit]

    async def get_product_overview(self, product_id: uuid.UUID) -> dict[str, Any]:
        return self._product_overviews.get(
            product_id,
            {
                "sources": [],
                "run": None,
                "review_cases": [],
                "product_context_snapshot": None,
            },
        )

    async def load_active_style_pack(self) -> object:
        if not self._style_guide_ready:
            raise RuntimeError("Aucun style pack actif disponible.")

        return object()

    async def select_commercial_signal_snapshot(
        self,
        *,
        product: ProductSnapshot,
    ) -> object:
        _ = product

        if not self._commercial_signals_ready:
            raise RuntimeError("Aucun snapshot commercial actif.")

        return object()

    async def list_product_taxonomies(self) -> tuple[ProductTaxonomySnapshot, ...]:
        return self._taxonomies

    async def create_product(
        self,
        *,
        sku: str,
        name: str,
        famille_code: str,
        sous_famille_code: str | None,
        season_code: str | None,
        segment_prix_code: str | None,
        langue_principale: str,
    ) -> ProductSnapshot:
        return ProductSnapshot(
            id=self._created_product_id or uuid.uuid4(),
            sku=sku,
            name=name,
            famille_code=famille_code,
            sous_famille_code=sous_famille_code,
            season_code=season_code,
            segment_prix_code=segment_prix_code,
            langue_principale=langue_principale,
        )


class _FakeProductLifecycleWorkflowStarter:
    def __init__(self) -> None:
        self.started_product: ProductContextReference | None = None

    async def start_product_lifecycle(self, product: ProductContextReference) -> str:
        self.started_product = product

        return f"product-lifecycle-{product.sku}"
