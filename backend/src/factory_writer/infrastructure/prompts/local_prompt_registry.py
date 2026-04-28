from importlib import import_module, resources
from types import ModuleType
from typing import Any

from factory_writer.application.ports.reasoning import ReasoningLevel
from factory_writer.application.ports.style_guide_ingestion import (
    PromptDefinition,
    PromptLLMConfig,
    PromptMessage,
    PromptRegistryPort,
    PromptSelector,
)

_PROMPTS_PACKAGE = "factory_writer.application.prompts"


class LocalStyleGuidePromptRegistry(PromptRegistryPort):
    async def get_prompt(self, selector: PromptSelector) -> PromptDefinition:
        manifest = _load_manifest(selector.name, selector.version)
        prompt_module = f"{_PROMPTS_PACKAGE}.{selector.name}.{selector.version}"

        return PromptDefinition(
            registry_provider="local",
            name=selector.name,
            version=selector.version,
            llm_config=_llm_config_from_manifest(manifest),
            messages=(
                PromptMessage(
                    role="system",
                    content=_read_template(
                        prompt_module,
                        manifest.SYSTEM_TEMPLATE_FILE,
                    ),
                ),
                PromptMessage(
                    role="user",
                    content=_read_template(
                        prompt_module,
                        manifest.USER_TEMPLATE_FILE,
                    ),
                ),
            ),
        )


class LocalPromptRegistry(LocalStyleGuidePromptRegistry):
    """Alias générique du registry local, conservant la compatibilité style guide."""


def _load_manifest(prompt_name: str, version: str) -> ModuleType:
    module_path = f"{_PROMPTS_PACKAGE}.{prompt_name}.{version}.manifest"
    try:
        return import_module(module_path)
    except ModuleNotFoundError as exc:
        raise ValueError(f"Prompt local introuvable: {prompt_name}/{version}") from exc


def _read_template(prompt_module: str, file_name: str) -> str:
    return resources.files(prompt_module).joinpath(file_name).read_text("utf-8").strip()


def _llm_config_from_manifest(manifest: ModuleType) -> PromptLLMConfig:
    config: dict[str, Any] = manifest.LLM_CONFIG
    return PromptLLMConfig(
        model=str(config["model"]),
        temperature=float(config["temperature"]),
        max_tokens=int(config["max_tokens"]),
        reasoning_level=_reasoning_level_from_manifest(config),
        response_format=dict(config["response_format"]),
    )


def _reasoning_level_from_manifest(config: dict[str, Any]) -> ReasoningLevel | None:
    if config.get("reasoning_level") is not None:
        return _coerce_reasoning_level(config["reasoning_level"])
    if config.get("reasoning_effort") is not None:
        return _legacy_reasoning_effort_to_level(config["reasoning_effort"])
    return None


def _coerce_reasoning_level(value: Any) -> ReasoningLevel:
    normalized = str(value).strip().lower()
    if normalized not in {"none", "minimal", "low", "medium", "high"}:
        raise ValueError(f"reasoning_level invalide dans le manifest prompt: {value}")
    return normalized  # type: ignore[return-value]


def _legacy_reasoning_effort_to_level(value: Any) -> ReasoningLevel:
    normalized = str(value).strip().lower()
    mapping = {
        "none": "none",
        "disable": "none",
        "minimal": "minimal",
        "low": "low",
        "medium": "medium",
        "high": "high",
        "xhigh": "high",
        "default": "medium",
    }
    try:
        return mapping[normalized]  # type: ignore[return-value]
    except KeyError as exc:
        raise ValueError(
            f"reasoning_effort legacy invalide dans le manifest prompt: {value}"
        ) from exc
