from enum import StrEnum


class WorkerRole(StrEnum):
    ORCHESTRATOR = "orchestrator"
    DOCAI = "docai"
    LLM = "llm"
    STYLE_ADMIN = "style-admin"
    OFFLINE_LAB = "offline-lab"


_ALIASES: dict[str, WorkerRole] = {
    WorkerRole.ORCHESTRATOR.value: WorkerRole.ORCHESTRATOR,
    "worker-orchestrator": WorkerRole.ORCHESTRATOR,
    WorkerRole.DOCAI.value: WorkerRole.DOCAI,
    "worker-docai": WorkerRole.DOCAI,
    WorkerRole.LLM.value: WorkerRole.LLM,
    "worker-llm": WorkerRole.LLM,
    WorkerRole.STYLE_ADMIN.value: WorkerRole.STYLE_ADMIN,
    "worker-style-admin": WorkerRole.STYLE_ADMIN,
    WorkerRole.OFFLINE_LAB.value: WorkerRole.OFFLINE_LAB,
    "worker-offline-lab": WorkerRole.OFFLINE_LAB,
    "admin-lab": WorkerRole.OFFLINE_LAB,
}


def parse_worker_role(raw_role: str) -> WorkerRole:
    normalized = raw_role.strip().lower()
    try:
        return _ALIASES[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(_ALIASES))
        raise ValueError(f"Unsupported WORKER_ROLE `{raw_role}`. Supported values: {supported}") from exc

