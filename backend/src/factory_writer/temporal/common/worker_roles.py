from enum import StrEnum


class WorkerRole(StrEnum):
    SKU_LIFECYCLE = "sku-lifecycle"
    STYLE_GUIDE_INGESTION = "style-guide-ingestion"
    OFFLINE_EVALUATION = "offline-evaluation"


_ALIASES: dict[str, WorkerRole] = {
    WorkerRole.SKU_LIFECYCLE.value: WorkerRole.SKU_LIFECYCLE,
    "orchestrator": WorkerRole.SKU_LIFECYCLE,
    "worker-orchestrator": WorkerRole.SKU_LIFECYCLE,
    "docai": WorkerRole.SKU_LIFECYCLE,
    "worker-docai": WorkerRole.SKU_LIFECYCLE,
    "llm": WorkerRole.SKU_LIFECYCLE,
    "worker-llm": WorkerRole.SKU_LIFECYCLE,
    WorkerRole.STYLE_GUIDE_INGESTION.value: WorkerRole.STYLE_GUIDE_INGESTION,
    "style-admin": WorkerRole.STYLE_GUIDE_INGESTION,
    "worker-style-admin": WorkerRole.STYLE_GUIDE_INGESTION,
    WorkerRole.OFFLINE_EVALUATION.value: WorkerRole.OFFLINE_EVALUATION,
    "offline-lab": WorkerRole.OFFLINE_EVALUATION,
    "worker-offline-lab": WorkerRole.OFFLINE_EVALUATION,
    "admin-lab": WorkerRole.OFFLINE_EVALUATION,
}


def parse_worker_role(raw_role: str) -> WorkerRole:
    normalized = raw_role.strip().lower()
    try:
        return _ALIASES[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(_ALIASES))
        raise ValueError(
            f"Unsupported WORKER_ROLE `{raw_role}`. Supported values: {supported}"
        ) from exc
