from enum import StrEnum


class WorkerRole(StrEnum):
    PRODUCT_LIFECYCLE = "product-lifecycle"
    STYLE_GUIDE_INGESTION = "style-guide-ingestion"


_ROLES_BY_VALUE: dict[str, WorkerRole] = {role.value: role for role in WorkerRole}


def parse_worker_role(raw_role: str) -> WorkerRole:
    normalized = raw_role.strip().lower()
    try:
        return _ROLES_BY_VALUE[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(_ROLES_BY_VALUE))
        raise ValueError(
            f"Unsupported WORKER_ROLE `{raw_role}`. Supported values: {supported}"
        ) from exc
