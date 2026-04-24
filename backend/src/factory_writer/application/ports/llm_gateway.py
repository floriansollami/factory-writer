from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from .reasoning import ReasoningLevel

LLMRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class LLMMessage:
    role: LLMRole
    content: str


@dataclass(frozen=True)
class LLMCompletionRequest:
    model: str
    messages: tuple[LLMMessage, ...]
    temperature: float
    max_tokens: int
    response_format: dict[str, Any]
    timeout_seconds: float
    reasoning_level: ReasoningLevel | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMCompletionResponse:
    content: str


class LLMGatewayPort(Protocol):
    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse: ...
