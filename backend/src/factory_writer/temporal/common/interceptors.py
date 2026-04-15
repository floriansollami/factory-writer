from __future__ import annotations

from typing import Any

from temporalio.exceptions import ApplicationError
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
)

from factory_writer.domain.exceptions import FactoryWriterError


class DomainErrorActivityInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        try:
            return await self.next.execute_activity(input)
        except FactoryWriterError as exc:
            raise ApplicationError(
                exc.message,
                type=exc.code,
                non_retryable=not exc.retryable,
            ) from exc


class DomainErrorInterceptor(Interceptor):
    def intercept_activity(
        self, next_interceptor: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return DomainErrorActivityInterceptor(next_interceptor)
