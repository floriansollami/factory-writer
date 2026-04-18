from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

from temporalio.common import RetryPolicy


class TaskQueue(StrEnum):
    SKU_LIFECYCLE = "sku-lifecycle"
    STYLE_GUIDE_INGESTION = "style-guide-ingestion"
    OFFLINE_EVALUATION = "offline-evaluation"


NON_RETRYABLE_ERRORS = [
    "ValueError",
    "KeyError",
    "RuntimeError",
    "AttributeError",
    "TypeError",
    "NotImplementedError",
    "InvalidArgument",
    "FailedPrecondition",
    "PermissionDenied",
    "Unauthenticated",
    "NotFound",
    "FileNotFoundError",
]

DB_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
    non_retryable_error_types=NON_RETRYABLE_ERRORS,
)

DOC_AI_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=5,
    non_retryable_error_types=NON_RETRYABLE_ERRORS,
)

DOC_AI_START_RETRY_POLICY = RetryPolicy(
    maximum_attempts=1,
    non_retryable_error_types=NON_RETRYABLE_ERRORS,
)

LLM_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=3,
    non_retryable_error_types=NON_RETRYABLE_ERRORS,
)

OFFLINE_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3,
    non_retryable_error_types=NON_RETRYABLE_ERRORS,
)

DB_ACTIVITY_TIMEOUT = timedelta(seconds=15)
SHORT_ACTIVITY_TIMEOUT = timedelta(minutes=1)
MEDIUM_ACTIVITY_TIMEOUT = timedelta(minutes=5)
LONG_ACTIVITY_TIMEOUT = timedelta(minutes=15)
DOC_AI_POLL_INTERVAL = timedelta(seconds=10)
HUMAN_APPROVAL_TIMEOUT = timedelta(days=7)
