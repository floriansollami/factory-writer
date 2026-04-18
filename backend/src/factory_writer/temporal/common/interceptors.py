from __future__ import annotations

from typing import Any

from temporalio.exceptions import ApplicationError
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
)


class DomainErrorActivityInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        try:
            return await self.next.execute_activity(input)
        except (ValueError, KeyError, FileNotFoundError) as exc:
            raise ApplicationError(
                str(exc),
                type=type(exc).__name__,
                non_retryable=True,
            ) from exc


class DomainErrorInterceptor(Interceptor):
    def intercept_activity(
        self, next_interceptor: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return DomainErrorActivityInterceptor(next_interceptor)
