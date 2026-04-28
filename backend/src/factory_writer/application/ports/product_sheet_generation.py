from dataclasses import dataclass
from typing import Any, Protocol

from factory_writer.application.ports.style_guide_ingestion import PreparedPrompt


@dataclass(frozen=True)
class ProductSheetGeneratorMetadata:
    prompt_registry_provider: str
    prompt_name: str
    prompt_version: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    llm_response_format: str
    system_prompt_hash: str
    user_prompt_hash: str


@dataclass(frozen=True)
class ProductSheetGeneratorResult:
    sheet_json: dict[str, Any]
    self_check_json: dict[str, Any]
    metadata: ProductSheetGeneratorMetadata


class ProductSheetGeneratorPort(Protocol):
    async def generate_product_sheet(
        self,
        prompt: PreparedPrompt,
    ) -> ProductSheetGeneratorResult: ...
