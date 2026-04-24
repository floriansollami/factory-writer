from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from time import monotonic, sleep
from urllib.parse import quote
from urllib.request import urlopen
from uuid import UUID

import docker  # type: ignore[import-untyped]
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from google.cloud.storage import Client as GcsClient  # type: ignore[import-untyped]
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from testcontainers.core.container import DockerContainer  # type: ignore[import-untyped]
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from factory_writer.application.ports.style_guide_ingestion import StyleGuideIngestionInput
from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    DecisionEditorialeStyleRule,
    OrigineStyleRule,
    StatutDocumentCollection,
    StatutDocumentIngestionRun,
    StatutStylePack,
)
from factory_writer.domain.style_guide_types import NiveauContrainte, StatutSource, TypeRegle
from factory_writer.infrastructure.database.models import (
    Base,
    DocumentCollection,
    DocumentIngestionRun,
    DocumentSource,
    StylePack,
    StyleRule,
    TaxonomieProduit,
)
from factory_writer.infrastructure.database.repositories.style_guide_repository import (
    StyleGuideRepository,
)
from factory_writer.temporal.client import get_temporal_client

_TEST_BUCKET_NAME = "factory-writer-style-guide-test"
_FAKE_GCS_PORT = 4443


@dataclass(frozen=True)
class AppTestContext:
    app: FastAPI
    client: AsyncClient


@dataclass(frozen=True)
class FakeTemporalStartCall:
    workflow: object
    payload: StyleGuideIngestionInput
    kwargs: dict[str, object]


@dataclass(frozen=True)
class FakeTemporalUpdateCall:
    workflow_id: str
    update_name: str
    style_pack_id: str


@dataclass(frozen=True)
class ReviewDraftFixture:
    ingestion_run_id: UUID
    style_pack_id: UUID
    llm_rule_ids: tuple[UUID, UUID]
    taxonomy_code: str


class FakeTemporalWorkflowHandle:
    def __init__(
        self,
        *,
        workflow_id: str,
        update_calls: list[FakeTemporalUpdateCall],
        on_approve: Callable[[str, str], Awaitable[None]] | None,
        on_reject: Callable[[str, str], Awaitable[None]] | None,
    ) -> None:
        self._workflow_id = workflow_id
        self._update_calls = update_calls
        self._on_approve = on_approve
        self._on_reject = on_reject
        self._pending_update_name: str | None = None
        self._pending_style_pack_id: str | None = None

    async def execute_update(
        self,
        update_method: object,
        style_pack_id: str,
    ) -> None:
        update_name = getattr(update_method, "__name__", str(update_method))
        self._pending_update_name = update_name
        self._pending_style_pack_id = style_pack_id
        self._update_calls.append(
            FakeTemporalUpdateCall(
                workflow_id=self._workflow_id,
                update_name=update_name,
                style_pack_id=style_pack_id,
            )
        )

    async def result(self) -> None:
        if self._pending_update_name is None or self._pending_style_pack_id is None:
            return

        if self._pending_update_name == "approve_style_pack" and self._on_approve is not None:
            await self._on_approve(self._workflow_id, self._pending_style_pack_id)
            return

        if self._pending_update_name == "reject_style_pack" and self._on_reject is not None:
            await self._on_reject(self._workflow_id, self._pending_style_pack_id)
            return


class FakeTemporalClient:
    def __init__(
        self,
        *,
        on_approve: Callable[[str, str], Awaitable[None]] | None = None,
        on_reject: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> None:
        self.calls: list[FakeTemporalStartCall] = []
        self.update_calls: list[FakeTemporalUpdateCall] = []
        self._on_approve = on_approve
        self._on_reject = on_reject
        self._handles: dict[str, FakeTemporalWorkflowHandle] = {}

    async def start_workflow(
        self,
        workflow: object,
        payload: StyleGuideIngestionInput,
        **kwargs: object,
    ) -> object:
        self.calls.append(FakeTemporalStartCall(workflow=workflow, payload=payload, kwargs=kwargs))
        return object()

    def get_workflow_handle(self, workflow_id: str) -> FakeTemporalWorkflowHandle:
        if workflow_id not in self._handles:
            self._handles[workflow_id] = FakeTemporalWorkflowHandle(
                workflow_id=workflow_id,
                update_calls=self.update_calls,
                on_approve=self._on_approve,
                on_reject=self._on_reject,
            )
        return self._handles[workflow_id]


@pytest.fixture(scope="module", autouse=True)
def require_docker_runtime() -> Iterator[None]:
    try:
        docker.from_env().ping()
    except docker.errors.DockerException as exc:
        pytest.skip(f"Docker daemon indisponible pour ce test d'integration: {exc}")
    yield


@pytest.fixture(scope="module")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:16-alpine", driver=None) as container:
        yield container


@pytest.fixture(scope="module")
def fake_gcs_container() -> Iterator[DockerContainer]:
    container = DockerContainer("fsouza/fake-gcs-server:1.54.0")
    container.with_command(f"-scheme http -port {_FAKE_GCS_PORT}")
    container.with_exposed_ports(_FAKE_GCS_PORT)
    container.start()
    _wait_for_fake_gcs(
        container.get_container_host_ip(),
        container.get_exposed_port(_FAKE_GCS_PORT),
    )
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="module")
def test_environment(
    postgres_container: PostgresContainer,
    fake_gcs_container: DockerContainer,
) -> Iterator[dict[str, str]]:
    db_url = postgres_container.get_connection_url(driver="psycopg")

    gcs_host = fake_gcs_container.get_container_host_ip()
    gcs_port = fake_gcs_container.get_exposed_port(_FAKE_GCS_PORT)
    storage_emulator_host = f"http://{gcs_host}:{gcs_port}"

    previous_env = {
        "DB__URL": os.environ.get("DB__URL"),
        "GCP__PROJECT_ID": os.environ.get("GCP__PROJECT_ID"),
        "GCP__STYLE_GUIDE_BUCKET_NAME": os.environ.get("GCP__STYLE_GUIDE_BUCKET_NAME"),
        "GCP__STORAGE_EMULATOR_HOST": os.environ.get("GCP__STORAGE_EMULATOR_HOST"),
    }
    os.environ["DB__URL"] = db_url
    os.environ["GCP__PROJECT_ID"] = "factory-writer-test"
    os.environ["GCP__STYLE_GUIDE_BUCKET_NAME"] = _TEST_BUCKET_NAME
    os.environ["GCP__STORAGE_EMULATOR_HOST"] = storage_emulator_host

    try:
        _initialize_database(db_url)
        _ensure_fake_gcs_bucket(storage_emulator_host)
        yield {
            "db_url": db_url,
            "storage_emulator_host": storage_emulator_host,
        }
    finally:
        for key, previous_value in previous_env.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value


@pytest.fixture
async def app_and_client(test_environment: dict[str, str]) -> AsyncIterator[AppTestContext]:
    app = _load_test_app()

    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield AppTestContext(app=app, client=client)


@pytest.mark.anyio
async def test_upload_style_guide_pdf_creates_gcs_object_and_db_rows(
    app_and_client: AppTestContext,
    test_environment: dict[str, str],
) -> None:
    pdf_bytes = _sample_pdf_bytes()

    response = await app_and_client.client.post(
        "/api/style-guide/upload",
        files={"file": ("guide-style.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    document_source_id = payload["documentSourceId"]

    assert payload["status"] == "EN_ATTENTE"
    assert payload["fileName"] == "guide-style.pdf"
    assert payload["storageUri"].startswith(f"gs://{_TEST_BUCKET_NAME}/sources/style-guides/")
    assert f"/{document_source_id}/" in payload["storageUri"]
    assert payload["storageGeneration"]
    assert payload["storageMetageneration"]

    _assert_gcs_object_exists(
        storage_emulator_host=test_environment["storage_emulator_host"],
        storage_uri=payload["storageUri"],
        expected_content_type="application/pdf",
        expected_bytes=pdf_bytes,
    )

    await _assert_database_rows(
        db_url=test_environment["db_url"],
        document_source_id=UUID(payload["documentSourceId"]),
        storage_uri=payload["storageUri"],
        generation=payload["storageGeneration"],
        metageneration=payload["storageMetageneration"],
        expected_size=len(pdf_bytes),
    )


@pytest.mark.anyio
async def test_start_style_guide_ingestion_creates_run_and_updates_statuses(
    app_and_client: AppTestContext,
    test_environment: dict[str, str],
) -> None:
    pdf_bytes = _sample_pdf_bytes()
    fake_temporal_client = FakeTemporalClient()
    app_and_client.app.dependency_overrides[get_temporal_client] = lambda: fake_temporal_client

    try:
        upload_response = await app_and_client.client.post(
            "/api/style-guide/upload",
            files={"file": ("guide-style-start.pdf", pdf_bytes, "application/pdf")},
        )
        assert upload_response.status_code == 201
        upload_payload = upload_response.json()

        start_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{upload_payload['documentSourceId']}/start-ingestion"
        )

        assert start_response.status_code == 202
        start_payload = start_response.json()

        assert start_payload["status"] == "EN_COURS"
        assert start_payload["documentSourceId"] == upload_payload["documentSourceId"]
        assert start_payload["storageUri"] == upload_payload["storageUri"]
        assert start_payload["workflowId"] == (
            f"style-guide-ingestion-{start_payload['ingestionRunId']}"
        )

        assert len(fake_temporal_client.calls) == 1
        temporal_call = fake_temporal_client.calls[0]
        temporal_payload = temporal_call.payload
        temporal_kwargs = temporal_call.kwargs

        assert str(temporal_payload.document_source_id) == upload_payload["documentSourceId"]
        assert str(temporal_payload.collection_id) == start_payload["collectionId"]
        assert str(temporal_payload.ingestion_run_id) == start_payload["ingestionRunId"]
        assert temporal_payload.storage_uri == upload_payload["storageUri"]
        assert temporal_kwargs["id"] == start_payload["workflowId"]
        assert temporal_kwargs["task_queue"] == "style-guide-ingestion"

        await _assert_ingestion_run_rows(
            db_url=test_environment["db_url"],
            document_source_id=UUID(upload_payload["documentSourceId"]),
            ingestion_run_id=UUID(start_payload["ingestionRunId"]),
            expected_workflow_id=start_payload["workflowId"],
        )
    finally:
        app_and_client.app.dependency_overrides.pop(get_temporal_client, None)


@pytest.mark.anyio
async def test_reupload_style_guide_creates_new_version_and_blocks_old_source(
    app_and_client: AppTestContext,
    test_environment: dict[str, str],
) -> None:
    original_pdf_bytes = _sample_pdf_bytes("original")
    reuploaded_pdf_bytes = _sample_pdf_bytes("reuploaded")
    fake_temporal_client = FakeTemporalClient()
    app_and_client.app.dependency_overrides[get_temporal_client] = lambda: fake_temporal_client

    try:
        original_upload_response = await app_and_client.client.post(
            "/api/style-guide/upload",
            files={"file": ("guide-style-original.pdf", original_pdf_bytes, "application/pdf")},
        )
        assert original_upload_response.status_code == 201
        original_payload = original_upload_response.json()

        reupload_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{original_payload['documentSourceId']}/reupload",
            files={"file": ("guide-style-reuploaded.pdf", reuploaded_pdf_bytes, "application/pdf")},
        )
        assert reupload_response.status_code == 201
        reupload_payload = reupload_response.json()

        assert reupload_payload["status"] == "EN_ATTENTE"
        assert reupload_payload["fileName"] == "guide-style-reuploaded.pdf"
        assert reupload_payload["documentSourceId"] != original_payload["documentSourceId"]
        assert f"/{reupload_payload['documentSourceId']}/" in reupload_payload["storageUri"]

        _assert_gcs_object_exists(
            storage_emulator_host=test_environment["storage_emulator_host"],
            storage_uri=reupload_payload["storageUri"],
            expected_content_type="application/pdf",
            expected_bytes=reuploaded_pdf_bytes,
        )

        await _assert_reupload_rows(
            db_url=test_environment["db_url"],
            previous_document_source_id=UUID(original_payload["documentSourceId"]),
            new_document_source_id=UUID(reupload_payload["documentSourceId"]),
            new_storage_uri=reupload_payload["storageUri"],
        )

        old_start_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{original_payload['documentSourceId']}/start-ingestion"
        )
        assert old_start_response.status_code == 409
        assert "remplac" in old_start_response.json()["detail"]

        second_reupload_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{original_payload['documentSourceId']}/reupload",
            files={"file": ("guide-style-again.pdf", reuploaded_pdf_bytes, "application/pdf")},
        )
        assert second_reupload_response.status_code == 409
        assert "déjà été remplacé" in second_reupload_response.json()["detail"]

        new_start_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{reupload_payload['documentSourceId']}/start-ingestion"
        )
        assert new_start_response.status_code == 202
        new_start_payload = new_start_response.json()
        assert new_start_payload["documentSourceId"] == reupload_payload["documentSourceId"]
        assert len(fake_temporal_client.calls) == 1
    finally:
        app_and_client.app.dependency_overrides.pop(get_temporal_client, None)


@pytest.mark.anyio
async def test_start_style_guide_ingestion_is_idempotent_under_concurrent_calls(
    app_and_client: AppTestContext,
    test_environment: dict[str, str],
) -> None:
    pdf_bytes = _sample_pdf_bytes("concurrent")
    fake_temporal_client = FakeTemporalClient()
    app_and_client.app.dependency_overrides[get_temporal_client] = lambda: fake_temporal_client

    try:
        upload_response = await app_and_client.client.post(
            "/api/style-guide/upload",
            files={"file": ("guide-style-concurrent.pdf", pdf_bytes, "application/pdf")},
        )
        assert upload_response.status_code == 201
        document_source_id = upload_response.json()["documentSourceId"]

        first_response, second_response = await asyncio.gather(
            app_and_client.client.post(
                f"/api/style-guide/document-sources/{document_source_id}/start-ingestion"
            ),
            app_and_client.client.post(
                f"/api/style-guide/document-sources/{document_source_id}/start-ingestion"
            ),
        )

        assert first_response.status_code == 202
        assert second_response.status_code == 202
        assert first_response.json()["ingestionRunId"] == second_response.json()["ingestionRunId"]
        assert first_response.json()["workflowId"] == second_response.json()["workflowId"]
        assert len(fake_temporal_client.calls) == 1
    finally:
        app_and_client.app.dependency_overrides.pop(get_temporal_client, None)


@pytest.mark.anyio
async def test_style_guide_overview_and_review_actions_round_trip(
    app_and_client: AppTestContext,
    test_environment: dict[str, str],
) -> None:
    fake_temporal_client = _build_review_temporal_client(test_environment["db_url"])
    app_and_client.app.dependency_overrides[get_temporal_client] = lambda: fake_temporal_client

    try:
        upload_response = await app_and_client.client.post(
            "/api/style-guide/upload",
            files={
                "file": ("guide-style-review.pdf", _sample_pdf_bytes("review"), "application/pdf")
            },
        )
        assert upload_response.status_code == 201
        upload_payload = upload_response.json()

        overview_after_upload = await app_and_client.client.get("/api/style-guide/overview")
        assert overview_after_upload.status_code == 200
        overview_upload_payload = overview_after_upload.json()
        assert overview_upload_payload["activePack"] is None
        assert overview_upload_payload["currentWorkflow"] is None
        assert (
            overview_upload_payload["pendingDocumentSource"]["documentSourceId"]
            == upload_payload["documentSourceId"]
        )

        start_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{upload_payload['documentSourceId']}/start-ingestion"
        )
        assert start_response.status_code == 202
        start_payload = start_response.json()

        review_fixture = await _seed_review_draft_pack(
            db_url=test_environment["db_url"],
            document_source_id=UUID(upload_payload["documentSourceId"]),
        )

        overview_response = await app_and_client.client.get("/api/style-guide/overview")
        assert overview_response.status_code == 200
        overview_payload = overview_response.json()
        assert overview_payload["pendingDocumentSource"] is None
        assert overview_payload["currentWorkflow"] is None
        assert overview_payload["activePack"]["id"] == str(review_fixture.style_pack_id)
        assert overview_payload["activePack"]["status"] == "BROUILLON"
        assert overview_payload["activePack"]["approvedBy"] is None
        assert overview_payload["activePack"]["approvedAt"] is None
        assert len(overview_payload["rules"]) == 2
        assert [rule["id"] for rule in overview_payload["rules"]] == [
            str(review_fixture.llm_rule_ids[0]),
            str(review_fixture.llm_rule_ids[1]),
        ]

        first_rule_id = str(review_fixture.llm_rule_ids[0])
        second_rule_id = str(review_fixture.llm_rule_ids[1])

        modify_response = await app_and_client.client.patch(
            f"/api/style-guide/packs/{review_fixture.style_pack_id}/rules/{first_rule_id}",
            json={
                "texteRegle": "Employer systématiquement le vouvoiement dans toutes les prises de parole.",
            },
        )
        assert modify_response.status_code == 204

        overview_after_modify = await app_and_client.client.get("/api/style-guide/overview")
        assert overview_after_modify.status_code == 200
        overview_after_modify_payload = overview_after_modify.json()
        assert [rule["id"] for rule in overview_after_modify_payload["rules"][:2]] == [
            str(review_fixture.llm_rule_ids[0]),
            str(review_fixture.llm_rule_ids[1]),
        ]
        modified_rule = next(
            rule for rule in overview_after_modify_payload["rules"] if rule["id"] == first_rule_id
        )
        assert (
            modified_rule["texteRegle"]
            == "Employer systématiquement le vouvoiement dans toutes les prises de parole."
        )
        assert modified_rule["origine"] == "MODIFIEE"

        patch_response = await app_and_client.client.patch(
            f"/api/style-guide/packs/{review_fixture.style_pack_id}/rules/{first_rule_id}",
            json={
                "decisionEditoriale": "APPROUVEE",
                "commentaire": "Validée par Sophie",
            },
        )
        assert patch_response.status_code == 204

        approve_too_early_response = await app_and_client.client.post(
            f"/api/style-guide/packs/{review_fixture.style_pack_id}/approve"
        )
        assert approve_too_early_response.status_code == 409
        assert "Toutes les règles" in approve_too_early_response.json()["detail"]

        patch_second_rule_response = await app_and_client.client.patch(
            f"/api/style-guide/packs/{review_fixture.style_pack_id}/rules/{second_rule_id}",
            json={
                "decisionEditoriale": "DESACTIVEE",
                "commentaire": "Hors périmètre pour cette version.",
            },
        )
        assert patch_second_rule_response.status_code == 204

        approve_response = await app_and_client.client.post(
            f"/api/style-guide/packs/{review_fixture.style_pack_id}/approve"
        )
        assert approve_response.status_code == 200
        assert approve_response.json() == {
            "status": "completed",
            "stylePackId": str(review_fixture.style_pack_id),
        }

        assert fake_temporal_client.update_calls[-1].workflow_id == start_payload["workflowId"]
        assert fake_temporal_client.update_calls[-1].update_name == "approve_style_pack"

        final_overview_response = await app_and_client.client.get("/api/style-guide/overview")
        assert final_overview_response.status_code == 200
        final_overview_payload = final_overview_response.json()
        assert final_overview_payload["activePack"]["status"] == "ACTIF"
        assert final_overview_payload["activePack"]["approvedBy"] == "Sophie"
        assert final_overview_payload["pendingDocumentSource"] is None
        assert final_overview_payload["currentWorkflow"] is None
        assert final_overview_payload["metrics"] == {
            "activeRules": 1,
            "needsReview": 0,
            "disabledRules": 1,
            "missingProvenance": 0,
        }

        await _assert_approved_pack_rows(
            db_url=test_environment["db_url"],
            style_pack_id=review_fixture.style_pack_id,
            ingestion_run_id=review_fixture.ingestion_run_id,
            document_source_id=UUID(upload_payload["documentSourceId"]),
        )
    finally:
        app_and_client.app.dependency_overrides.pop(get_temporal_client, None)


@pytest.mark.anyio
async def test_style_guide_review_rejects_invalid_rule_payloads(
    app_and_client: AppTestContext,
    test_environment: dict[str, str],
) -> None:
    fake_temporal_client = _build_review_temporal_client(test_environment["db_url"])
    app_and_client.app.dependency_overrides[get_temporal_client] = lambda: fake_temporal_client

    try:
        upload_response = await app_and_client.client.post(
            "/api/style-guide/upload",
            files={
                "file": ("guide-style-review.pdf", _sample_pdf_bytes("review"), "application/pdf")
            },
        )
        assert upload_response.status_code == 201
        upload_payload = upload_response.json()

        start_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{upload_payload['documentSourceId']}/start-ingestion"
        )
        assert start_response.status_code == 202

        review_fixture = await _seed_review_draft_pack(
            db_url=test_environment["db_url"],
            document_source_id=UUID(upload_payload["documentSourceId"]),
        )
        first_rule_id = str(review_fixture.llm_rule_ids[0])

        invalid_patch_response = await app_and_client.client.patch(
            f"/api/style-guide/packs/{review_fixture.style_pack_id}/rules/{first_rule_id}",
            json={"typeRegle": "TON"},
        )
        assert invalid_patch_response.status_code == 400
        assert "famille produit" in invalid_patch_response.json()["detail"]

        invalid_claim_patch_response = await app_and_client.client.patch(
            f"/api/style-guide/packs/{review_fixture.style_pack_id}/rules/{first_rule_id}",
            json={"typeRegle": "PROMESSE_INTERDITE", "niveauContrainte": "SOFT"},
        )
        assert invalid_claim_patch_response.status_code == 400
        assert "niveau HARD" in invalid_claim_patch_response.json()["detail"]

        invalid_text_response = await app_and_client.client.patch(
            f"/api/style-guide/packs/{review_fixture.style_pack_id}/rules/{first_rule_id}",
            json={"texteRegle": " court "},
        )
        assert invalid_text_response.status_code == 400
        assert "explicite" in invalid_text_response.json()["detail"]
    finally:
        app_and_client.app.dependency_overrides.pop(get_temporal_client, None)


@pytest.mark.anyio
async def test_approving_new_pack_archives_previous_active_pack(
    app_and_client: AppTestContext,
    test_environment: dict[str, str],
) -> None:
    fake_temporal_client = _build_review_temporal_client(test_environment["db_url"])
    app_and_client.app.dependency_overrides[get_temporal_client] = lambda: fake_temporal_client

    try:
        first_upload_response = await app_and_client.client.post(
            "/api/style-guide/upload",
            files={
                "file": ("guide-style-v1.pdf", _sample_pdf_bytes("review-v1"), "application/pdf")
            },
        )
        assert first_upload_response.status_code == 201
        first_document_source_id = UUID(first_upload_response.json()["documentSourceId"])

        first_start_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{first_document_source_id}/start-ingestion"
        )
        assert first_start_response.status_code == 202

        first_fixture = await _seed_review_draft_pack(
            db_url=test_environment["db_url"],
            document_source_id=first_document_source_id,
        )
        await _mark_pack_rules_approved(
            db_url=test_environment["db_url"],
            style_pack_id=first_fixture.style_pack_id,
        )
        await _finalize_pack(
            db_url=test_environment["db_url"],
            style_pack_id=first_fixture.style_pack_id,
            action="approve",
        )

        second_upload_response = await app_and_client.client.post(
            "/api/style-guide/upload",
            files={
                "file": ("guide-style-v2.pdf", _sample_pdf_bytes("review-v2"), "application/pdf")
            },
        )
        assert second_upload_response.status_code == 201
        second_document_source_id = UUID(second_upload_response.json()["documentSourceId"])

        second_start_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{second_document_source_id}/start-ingestion"
        )
        assert second_start_response.status_code == 202

        second_fixture = await _seed_review_draft_pack(
            db_url=test_environment["db_url"],
            document_source_id=second_document_source_id,
        )
        await _mark_pack_rules_approved(
            db_url=test_environment["db_url"],
            style_pack_id=second_fixture.style_pack_id,
        )
        await _finalize_pack(
            db_url=test_environment["db_url"],
            style_pack_id=second_fixture.style_pack_id,
            action="approve",
        )

        await _assert_only_latest_pack_is_active(
            db_url=test_environment["db_url"],
            previous_style_pack_id=first_fixture.style_pack_id,
            current_style_pack_id=second_fixture.style_pack_id,
        )

        overview_response = await app_and_client.client.get("/api/style-guide/overview")
        assert overview_response.status_code == 200
        overview_payload = overview_response.json()

        assert overview_payload["activePack"]["id"] == str(second_fixture.style_pack_id)
        assert [pack["version"] for pack in overview_payload["recentPacks"][:2]] == [
            str(second_fixture.style_pack_id),
            str(first_fixture.style_pack_id),
        ]
        assert [pack["status"] for pack in overview_payload["recentPacks"][:2]] == [
            "ACTIF",
            "ARCHIVE",
        ]
    finally:
        app_and_client.app.dependency_overrides.pop(get_temporal_client, None)


@pytest.mark.anyio
async def test_reject_style_guide_pack_archives_candidate_and_overview_falls_back_to_archive(
    app_and_client: AppTestContext,
    test_environment: dict[str, str],
) -> None:
    fake_temporal_client = _build_review_temporal_client(test_environment["db_url"])
    app_and_client.app.dependency_overrides[get_temporal_client] = lambda: fake_temporal_client

    try:
        upload_response = await app_and_client.client.post(
            "/api/style-guide/upload",
            files={
                "file": ("guide-style-reject.pdf", _sample_pdf_bytes("reject"), "application/pdf")
            },
        )
        assert upload_response.status_code == 201
        upload_payload = upload_response.json()

        start_response = await app_and_client.client.post(
            f"/api/style-guide/document-sources/{upload_payload['documentSourceId']}/start-ingestion"
        )
        assert start_response.status_code == 202
        start_payload = start_response.json()

        review_fixture = await _seed_review_draft_pack(
            db_url=test_environment["db_url"],
            document_source_id=UUID(upload_payload["documentSourceId"]),
        )

        reject_response = await app_and_client.client.post(
            f"/api/style-guide/packs/{review_fixture.style_pack_id}/reject"
        )
        assert reject_response.status_code == 200
        assert reject_response.json() == {
            "status": "rejected",
            "stylePackId": str(review_fixture.style_pack_id),
        }

        assert fake_temporal_client.update_calls[-1].workflow_id == start_payload["workflowId"]
        assert fake_temporal_client.update_calls[-1].update_name == "reject_style_pack"

        overview_response = await app_and_client.client.get("/api/style-guide/overview")
        assert overview_response.status_code == 200
        overview_payload = overview_response.json()
        assert overview_payload["activePack"]["status"] == "ARCHIVE"
        assert overview_payload["pendingDocumentSource"] is None
        assert overview_payload["currentWorkflow"] is None

        await _assert_rejected_pack_rows(
            db_url=test_environment["db_url"],
            style_pack_id=review_fixture.style_pack_id,
            ingestion_run_id=review_fixture.ingestion_run_id,
            document_source_id=UUID(upload_payload["documentSourceId"]),
        )
    finally:
        app_and_client.app.dependency_overrides.pop(get_temporal_client, None)


def _load_test_app() -> FastAPI:
    import factory_writer.api.routes.style_guide_admin_router as router_module
    import factory_writer.main as main_module
    from factory_writer.core.config import get_settings
    from factory_writer.infrastructure.database.session import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    refreshed_settings = get_settings()
    router_module.settings = refreshed_settings
    main_module.settings = refreshed_settings

    return main_module.app


def _build_review_temporal_client(db_url: str) -> FakeTemporalClient:
    async def _approve(_: str, style_pack_id: str) -> None:
        await _finalize_pack(db_url=db_url, style_pack_id=UUID(style_pack_id), action="approve")

    async def _reject(_: str, style_pack_id: str) -> None:
        await _finalize_pack(db_url=db_url, style_pack_id=UUID(style_pack_id), action="reject")

    return FakeTemporalClient(on_approve=_approve, on_reject=_reject)


async def _finalize_pack(
    *,
    db_url: str,
    style_pack_id: UUID,
    action: str,
) -> None:
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    repository = StyleGuideRepository(session_factory)

    try:
        if action == "approve":
            await repository.finalize_style_pack_approval(style_pack_id=style_pack_id)
            return

        if action == "reject":
            await repository.finalize_style_pack_rejection(style_pack_id=style_pack_id)
            return

        raise ValueError(f"Action de finalisation inconnue: {action}")
    finally:
        await engine.dispose()


async def _mark_pack_rules_approved(
    *,
    db_url: str,
    style_pack_id: UUID,
) -> None:
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session, session.begin():
            style_pack = await session.get(
                StylePack,
                style_pack_id,
                options=[selectinload(StylePack.style_rules)],
            )
            assert style_pack is not None

            for rule in style_pack.style_rules:
                rule.decision_editoriale = DecisionEditorialeStyleRule.APPROUVEE
                rule.commentaire_review = "Validée pour activation"
    finally:
        await engine.dispose()


async def _seed_review_draft_pack(
    *,
    db_url: str,
    document_source_id: UUID,
) -> ReviewDraftFixture:
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session, session.begin():
            document_source = await session.get(DocumentSource, document_source_id)
            assert document_source is not None

            collection = await session.get(DocumentCollection, document_source.collection_id)
            assert collection is not None

            ingestion_run = (
                await session.scalars(
                    select(DocumentIngestionRun)
                    .where(DocumentIngestionRun.collection_id == collection.id)
                    .order_by(DocumentIngestionRun.created_at.desc())
                    .limit(1)
                )
            ).one()

            ingestion_run.statut = StatutDocumentIngestionRun.A_VALIDER
            ingestion_run.current_step = CurrentStep.HUMAN_REVIEW
            collection.statut = StatutDocumentCollection.A_VALIDER
            document_source.statut = StatutSource.TERMINE

            taxonomy_code = f"TAXO-{document_source_id.hex[:8]}"
            taxonomy = TaxonomieProduit(
                famille_code=taxonomy_code,
                libelle_fr="Taxonomie locale de test",
            )
            session.add(taxonomy)
            await session.flush()

            style_pack = StylePack(
                ingestion_run_id=ingestion_run.id,
                statut=StatutStylePack.BROUILLON,
                est_actif=False,
                prompt_registry_provider="prompt-registry",
                prompt_name="style-guide-review-test",
                prompt_version="v1",
                llm_model="gpt-5.4-mini",
                llm_temperature=0.1,
                llm_max_tokens=2048,
                llm_response_format_name="DraftStylePackExtractionV1",
                rendered_system_prompt_hash="system-hash",
                rendered_user_prompt_hash="user-hash",
                validation_summary_json={"rules_generated": 2, "rules_to_review": 2},
            )
            session.add(style_pack)
            await session.flush()

            first_rule = StyleRule(
                pack_id=style_pack.id,
                taxonomie_produit_id=None,
                type_regle=TypeRegle.VOIX,
                niveau_contrainte=NiveauContrainte.HARD,
                texte_regle_original="Employer un ton rassurant.",
                texte_regle="Employer un ton rassurant.",
                decision_editoriale=DecisionEditorialeStyleRule.A_VALIDER,
                est_actif=False,
                origine=OrigineStyleRule.LLM,
                source_evidence_text="Le guide insiste sur une voix chaleureuse.",
                source_evidence_provider_id="docai-1",
                source_evidence_page_start=1,
                source_evidence_page_end=1,
                source_evidence_json={"provider_id": "docai-1", "index_chunk": 1},
            )
            second_rule = StyleRule(
                pack_id=style_pack.id,
                taxonomie_produit_id=taxonomy.id,
                type_regle=TypeRegle.TON,
                niveau_contrainte=NiveauContrainte.SOFT,
                texte_regle_original="Utiliser le vocabulaire de confort pour cette gamme.",
                texte_regle="Utiliser le vocabulaire de confort pour cette gamme.",
                decision_editoriale=DecisionEditorialeStyleRule.A_VALIDER,
                est_actif=False,
                origine=OrigineStyleRule.LLM,
                source_evidence_text="Le guide mentionne explicitement le confort premium.",
                source_evidence_provider_id="docai-2",
                source_evidence_page_start=2,
                source_evidence_page_end=2,
                source_evidence_json={"provider_id": "docai-2", "index_chunk": 2},
            )
            session.add_all([first_rule, second_rule])
            await session.flush()

            ingestion_run.validation_summary_json = {"rules_generated": 2, "rules_to_review": 2}

            return ReviewDraftFixture(
                ingestion_run_id=ingestion_run.id,
                style_pack_id=style_pack.id,
                llm_rule_ids=(first_rule.id, second_rule.id),
                taxonomy_code=taxonomy_code,
            )
    finally:
        await engine.dispose()


def _initialize_database(db_url: str) -> None:
    async def _run() -> None:
        engine = create_async_engine(db_url, future=True)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
                await connection.run_sync(Base.metadata.create_all)
        finally:
            await engine.dispose()

    import asyncio

    asyncio.run(_run())


def _ensure_fake_gcs_bucket(storage_emulator_host: str) -> None:
    client = GcsClient(
        project="factory-writer-test",
        client_options={"api_endpoint": storage_emulator_host},
        use_auth_w_custom_endpoint=False,
    )
    bucket = client.bucket(_TEST_BUCKET_NAME)
    if not bucket.exists():
        client.create_bucket(bucket)


def _assert_gcs_object_exists(
    *,
    storage_emulator_host: str,
    storage_uri: str,
    expected_content_type: str,
    expected_bytes: bytes,
) -> None:
    client = GcsClient(
        project="factory-writer-test",
        client_options={"api_endpoint": storage_emulator_host},
        use_auth_w_custom_endpoint=False,
    )

    bucket_name, object_name = _parse_gcs_uri(storage_uri)
    blob = client.bucket(bucket_name).get_blob(object_name)

    assert blob is not None
    assert blob.content_type == expected_content_type

    object_path = quote(object_name, safe="")
    download_url = (
        f"{storage_emulator_host}/download/storage/v1/b/{bucket_name}/o/{object_path}?alt=media"
    )
    with urlopen(download_url, timeout=5) as response:
        assert response.read() == expected_bytes


async def _assert_database_rows(
    *,
    db_url: str,
    document_source_id: UUID,
    storage_uri: str,
    generation: str,
    metageneration: str,
    expected_size: int,
) -> None:
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            document_source = await session.get(DocumentSource, document_source_id)
            assert document_source is not None
            assert document_source.storage_uri == storage_uri
            assert document_source.storage_generation == generation
            assert document_source.storage_metageneration == metageneration
            assert document_source.storage_content_type == "application/pdf"
            assert document_source.storage_size_bytes == expected_size
            assert document_source.statut.value == "EN_ATTENTE"

            document_collection = await session.get(
                DocumentCollection, document_source.collection_id
            )
            assert document_collection is not None
            assert document_collection.collection_kind.value == "STYLE_GUIDE"
            assert document_collection.statut.value == "EN_ATTENTE"
    finally:
        await engine.dispose()


async def _assert_ingestion_run_rows(
    *,
    db_url: str,
    document_source_id: UUID,
    ingestion_run_id: UUID,
    expected_workflow_id: str,
) -> None:
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            document_source = await session.get(DocumentSource, document_source_id)
            assert document_source is not None
            assert document_source.statut.value == "EN_COURS"
            assert document_source.dernier_message_erreur is None

            document_collection = await session.get(
                DocumentCollection, document_source.collection_id
            )
            assert document_collection is not None
            assert document_collection.statut.value == "EN_COURS"
            assert document_collection.dernier_message_erreur is None

            ingestion_run = await session.get(DocumentIngestionRun, ingestion_run_id)
            assert ingestion_run is not None
            assert ingestion_run.collection_id == document_collection.id
            assert ingestion_run.pipeline_kind == "STYLE_GUIDE_EXTRACTION"
            assert ingestion_run.statut.value == "EN_COURS"
            assert ingestion_run.current_step.value == "UPLOAD"
            assert ingestion_run.temporal_workflow_id == expected_workflow_id
            assert ingestion_run.error_message is None
            assert ingestion_run.started_at is not None
            assert ingestion_run.completed_at is None
    finally:
        await engine.dispose()


async def _assert_reupload_rows(
    *,
    db_url: str,
    previous_document_source_id: UUID,
    new_document_source_id: UUID,
    new_storage_uri: str,
) -> None:
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            previous_document_source = await session.get(
                DocumentSource, previous_document_source_id
            )
            assert previous_document_source is not None

            new_document_source = await session.get(DocumentSource, new_document_source_id)
            assert new_document_source is not None
            assert new_document_source.storage_uri == new_storage_uri
            assert new_document_source.statut.value == "EN_ATTENTE"

            previous_collection = await session.get(
                DocumentCollection, previous_document_source.collection_id
            )
            assert previous_collection is not None

            new_collection = await session.get(
                DocumentCollection, new_document_source.collection_id
            )
            assert new_collection is not None
            assert new_collection.id != previous_collection.id
            assert new_collection.collection_kind.value == "STYLE_GUIDE"
            assert new_collection.statut.value == "EN_ATTENTE"

            assert previous_document_source.replaced_by_source_id == new_document_source.id
            assert previous_collection.replaced_by_collection_id == new_collection.id
    finally:
        await engine.dispose()


async def _assert_approved_pack_rows(
    *,
    db_url: str,
    style_pack_id: UUID,
    ingestion_run_id: UUID,
    document_source_id: UUID,
) -> None:
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            style_pack = await session.get(StylePack, style_pack_id)
            assert style_pack is not None
            assert style_pack.statut == StatutStylePack.ACTIF
            assert style_pack.est_actif is True
            assert style_pack.approuve_le is not None

            ingestion_run = await session.get(DocumentIngestionRun, ingestion_run_id)
            assert ingestion_run is not None
            assert ingestion_run.statut == StatutDocumentIngestionRun.TERMINE
            assert ingestion_run.current_step == CurrentStep.DONE
            assert ingestion_run.completed_at is not None

            document_source = await session.get(DocumentSource, document_source_id)
            assert document_source is not None
            assert document_source.statut == StatutSource.TERMINE

            document_collection = await session.get(
                DocumentCollection, document_source.collection_id
            )
            assert document_collection is not None
            assert document_collection.statut == StatutDocumentCollection.TERMINE
    finally:
        await engine.dispose()


async def _assert_only_latest_pack_is_active(
    *,
    db_url: str,
    previous_style_pack_id: UUID,
    current_style_pack_id: UUID,
) -> None:
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            previous_style_pack = await session.get(StylePack, previous_style_pack_id)
            current_style_pack = await session.get(StylePack, current_style_pack_id)

            assert previous_style_pack is not None
            assert current_style_pack is not None

            assert previous_style_pack.statut == StatutStylePack.ARCHIVE
            assert previous_style_pack.est_actif is False
            assert current_style_pack.statut == StatutStylePack.ACTIF
            assert current_style_pack.est_actif is True

            active_packs = list(
                (
                    await session.scalars(select(StylePack).where(StylePack.est_actif.is_(True)))
                ).all()
            )
            assert [pack.id for pack in active_packs] == [current_style_pack_id]
    finally:
        await engine.dispose()


async def _assert_rejected_pack_rows(
    *,
    db_url: str,
    style_pack_id: UUID,
    ingestion_run_id: UUID,
    document_source_id: UUID,
) -> None:
    engine = create_async_engine(db_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            style_pack = await session.get(StylePack, style_pack_id)
            assert style_pack is not None
            assert style_pack.statut == StatutStylePack.ARCHIVE
            assert style_pack.est_actif is False
            assert style_pack.approuve_le is None

            ingestion_run = await session.get(DocumentIngestionRun, ingestion_run_id)
            assert ingestion_run is not None
            assert ingestion_run.statut == StatutDocumentIngestionRun.ANNULE
            assert ingestion_run.current_step == CurrentStep.HUMAN_REVIEW
            assert ingestion_run.completed_at is not None

            document_source = await session.get(DocumentSource, document_source_id)
            assert document_source is not None
            assert document_source.statut == StatutSource.TERMINE

            document_collection = await session.get(
                DocumentCollection, document_source.collection_id
            )
            assert document_collection is not None
            assert document_collection.statut == StatutDocumentCollection.TERMINE
    finally:
        await engine.dispose()


def _parse_gcs_uri(storage_uri: str) -> tuple[str, str]:
    bucket_name, _, object_name = storage_uri.removeprefix("gs://").partition("/")
    return bucket_name, object_name


def _sample_pdf_bytes(label: str = "sample") -> bytes:
    return b"".join(
        [
            b"%PDF-1.4\n",
            b"1 0 obj<<>>endobj\n",
            b"2 0 obj<< /Type /Catalog /Pages 3 0 R >>endobj\n",
            b"3 0 obj<< /Type /Pages /Kids [4 0 R] /Count 1 >>endobj\n",
            b"4 0 obj<< /Type /Page /Parent 3 0 R /MediaBox [0 0 300 144] >>endobj\n",
            f"% {label}\n".encode(),
            b"trailer<< /Root 2 0 R >>\n",
            b"%%EOF\n",
        ]
    )


def _wait_for_fake_gcs(host: str, port: str, timeout_seconds: float = 10.0) -> None:
    client = GcsClient(
        project="factory-writer-test",
        client_options={"api_endpoint": f"http://{host}:{port}"},
        use_auth_w_custom_endpoint=False,
    )

    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        try:
            list(client.list_buckets())
            return
        except Exception:
            sleep(0.2)

    raise RuntimeError("fake-gcs-server n'est pas devenu pret dans le delai imparti.")
