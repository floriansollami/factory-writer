from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import mstache

from factory_writer.application.ports.reasoning import ReasoningLevel

PromptRole = Literal["system", "user"]


@dataclass(frozen=True)
class PromptSelector:
    name: str
    version: str


@dataclass(frozen=True)
class PromptMessage:
    role: PromptRole
    content: str


@dataclass(frozen=True)
class PromptLLMConfig:
    model: str
    temperature: float
    max_tokens: int
    reasoning_level: ReasoningLevel | None
    response_format: Mapping[str, Any]


@dataclass(frozen=True)
class PreparedPrompt:
    registry_provider: str
    name: str
    version: str
    llm_config: PromptLLMConfig
    messages: tuple[PromptMessage, ...]


@dataclass(frozen=True)
class PromptDefinition:
    registry_provider: str
    name: str
    version: str
    llm_config: PromptLLMConfig
    messages: tuple[PromptMessage, ...]

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("Un prompt doit contenir au moins un message.")

    def compile(self, variables: Mapping[str, str]) -> PreparedPrompt:
        return PreparedPrompt(
            registry_provider=self.registry_provider,
            name=self.name,
            version=self.version,
            llm_config=self.llm_config,
            messages=tuple(
                PromptMessage(message.role, _render(message.content, variables))
                for message in self.messages
            ),
        )


class PromptRegistryPort(Protocol):
    async def get_prompt(self, selector: PromptSelector) -> PromptDefinition: ...


def _render(template: str, variables: Mapping[str, str]) -> str:
    return str(
        mstache.render(
            template,
            dict(variables),
            escape=_do_not_escape_prompt_values,
            strict=True,
        )
    ).strip()


def _do_not_escape_prompt_values(value: bytes) -> bytes:
    return value
