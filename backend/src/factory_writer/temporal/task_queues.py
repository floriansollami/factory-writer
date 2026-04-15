from enum import StrEnum


class TaskQueue(StrEnum):
    SKU_LIFECYCLE = "sku-lifecycle"
    DOCAI_ACTIVITIES = "docai-activities"
    LLM_GENERATION = "llm-generation"
    STYLE_INGESTION = "style-ingestion"
    OFFLINE_EVAL = "offline-eval"

