from __future__ import annotations

from datetime import timedelta

from temporalio.common import RetryPolicy

DB_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
)

DOC_AI_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=5,
)

LLM_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=3,
)

OFFLINE_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3,
)

SHORT_ACTIVITY_TIMEOUT = timedelta(minutes=1)
MEDIUM_ACTIVITY_TIMEOUT = timedelta(minutes=5)
LONG_ACTIVITY_TIMEOUT = timedelta(minutes=15)
HUMAN_APPROVAL_TIMEOUT = timedelta(days=7)
