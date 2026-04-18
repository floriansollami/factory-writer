from importlib import import_module, resources
from types import ModuleType
from typing import Any

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
        response_format=dict(config["response_format"]),
    )
