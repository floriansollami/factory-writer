from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from factory_writer.application.ports.product_technical_ingestion import ProductSnapshot
from factory_writer.infrastructure.database.models import CommercialSignalSnapshot
from factory_writer.infrastructure.database.repositories.product_repository_mappers import (
    _choose_commercial_snapshot,
    _commercial_snapshot_matches_product,
)


def test_commercial_snapshot_match_requires_exact_family_season_and_segment() -> None:
    product = _product_snapshot()
    exact_snapshot = _commercial_snapshot(
        famille_code="mobilier_jardin",
        season_code="printemps_ete",
        segment_prix_code="premium",
    )
    family_only_snapshot = _commercial_snapshot(
        famille_code="mobilier_jardin",
        season_code=None,
        segment_prix_code=None,
    )

    assert _commercial_snapshot_matches_product(
        product=product,
        snapshot=exact_snapshot,
    )
    assert not _commercial_snapshot_matches_product(
        product=product,
        snapshot=family_only_snapshot,
    )


def test_choose_commercial_snapshot_rejects_family_only_fallback() -> None:
    product = _product_snapshot()

    with pytest.raises(RuntimeError, match="Aucun snapshot commercial actif compatible"):
        _choose_commercial_snapshot(
            product,
            [
                _commercial_snapshot(
                    famille_code="mobilier_jardin",
                    season_code=None,
                    segment_prix_code=None,
                ),
            ],
        )


def test_choose_commercial_snapshot_returns_exact_match() -> None:
    product = _product_snapshot()

    snapshot, reason = _choose_commercial_snapshot(
        product,
        [
            _commercial_snapshot(
                famille_code="mobilier_jardin",
                season_code="printemps_ete",
                segment_prix_code="premium",
            ),
        ],
    )

    assert snapshot.snapshot_id == "sig_mobilier_jardin_premium_ss26"
    assert reason == "matched_family_segment_season"


def _product_snapshot() -> ProductSnapshot:
    return ProductSnapshot(
        id=uuid.uuid4(),
        sku="AX-TB-RIV-220-TKGR",
        name="Table Rivage 220",
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        season_code="printemps_ete",
        segment_prix_code="premium",
        langue_principale="fr-FR",
    )


def _commercial_snapshot(
    *,
    famille_code: str,
    season_code: str | None,
    segment_prix_code: str | None,
) -> CommercialSignalSnapshot:
    return CommercialSignalSnapshot(
        id=uuid.uuid4(),
        snapshot_id="sig_mobilier_jardin_premium_ss26",
        cohort_key=f"{famille_code}.{segment_prix_code}.{season_code}",
        famille_code=famille_code,
        season_code=season_code,
        segment_prix_code=segment_prix_code,
        sales_signals_json={},
        feedback_signals_json={},
        generated_at=datetime(2026, 4, 25, tzinfo=UTC),
        is_active=True,
    )
