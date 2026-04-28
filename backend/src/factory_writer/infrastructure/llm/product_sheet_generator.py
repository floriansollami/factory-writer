from __future__ import annotations

import hashlib
import json
from typing import Any

import structlog
from pydantic import ValidationError

from factory_writer.application.ports import LLMCompletionRequest, LLMGatewayPort, LLMMessage
from factory_writer.application.ports.product_sheet_generation import (
    ProductSheetGeneratorMetadata,
    ProductSheetGeneratorResult,
)
from factory_writer.application.ports.style_guide_ingestion import PreparedPrompt, PromptMessage
from factory_writer.application.prompts.product_sheet_generate.v1.output_schema import (
    ProductSheetCandidateV1,
)
from factory_writer.core.config import Settings

logger = structlog.get_logger(__name__)


class LiteLLMProductSheetGenerator:
    def __init__(self, settings: Settings, llm_gateway: LLMGatewayPort) -> None:
        self._settings = settings
        self._llm_gateway = llm_gateway

    async def generate_product_sheet(
        self,
        prompt: PreparedPrompt,
    ) -> ProductSheetGeneratorResult:
        llm_config = prompt.llm_config
        response_format = dict(llm_config.response_format)
        response_format_name = _response_format_name(response_format)

        response = await self._llm_gateway.complete(
            LLMCompletionRequest(
                model=llm_config.model,
                messages=tuple(
                    LLMMessage(role=message.role, content=message.content)
                    for message in prompt.messages
                ),
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                timeout_seconds=self._settings.llm.product_sheet_timeout_seconds,
                response_format=response_format,
                reasoning_level=llm_config.reasoning_level,
                metadata={
                    "prompt_registry_provider": prompt.registry_provider,
                    "prompt_name": prompt.name,
                    "prompt_version": prompt.version,
                    "response_format": response_format_name,
                },
            )
        )

        logger.info(
            "Product sheet | Génération | réponse LiteLLM JSON\n%s",
            _format_json_for_log(response.content),
        )

        candidate = _parse_candidate(response.content)
        return ProductSheetGeneratorResult(
            sheet_json=candidate.model_dump(mode="json"),
            self_check_json={
                "requires_human_review": candidate.requires_human_review,
                "human_review_reasons": candidate.human_review_reasons,
            },
            metadata=ProductSheetGeneratorMetadata(
                prompt_registry_provider=prompt.registry_provider,
                prompt_name=prompt.name,
                prompt_version=prompt.version,
                llm_model=llm_config.model,
                llm_temperature=llm_config.temperature,
                llm_max_tokens=llm_config.max_tokens,
                llm_response_format=response_format_name,
                system_prompt_hash=_hash_prompt(_first_message_content(prompt.messages, "system")),
                user_prompt_hash=_hash_prompt(_first_message_content(prompt.messages, "user")),
            ),
        )


def _parse_candidate(content: str) -> ProductSheetCandidateV1:
    try:
        return ProductSheetCandidateV1.model_validate_json(content)
    except ValidationError as exc:
        raise ValueError(f"Sortie LLM fiche produit invalide: {exc}") from exc


def _hash_prompt(prompt: str) -> str:
    return f"sha256:{hashlib.sha256(prompt.encode('utf-8')).hexdigest()}"


def _first_message_content(messages: tuple[PromptMessage, ...], role: str) -> str:
    for message in messages:
        if message.role == role:
            return message.content
    return ""


def _response_format_name(response_format: dict[str, Any]) -> str:
    try:
        name = response_format["json_schema"]["name"]
    except (KeyError, TypeError) as exc:
        raise ValueError("response_format json_schema.name manquant") from exc

    if not isinstance(name, str) or not name.strip():
        raise ValueError("response_format json_schema.name invalide")

    return name


def _format_json_for_log(content: str) -> str:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return content

    return json.dumps(parsed, ensure_ascii=False, indent=2)
