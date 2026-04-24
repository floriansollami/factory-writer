from typing import Any

import litellm
import structlog
from litellm.exceptions import AuthenticationError, BadRequestError, JSONSchemaValidationError

from factory_writer.application.ports import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    LLMGatewayPort,
    ReasoningLevel,
)
from factory_writer.core.config import Settings

logger = structlog.get_logger(__name__)


class LiteLLMGateway(LLMGatewayPort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        try:
            response = await _acompletion(request, self._settings, request.reasoning_level)
        except JSONSchemaValidationError:
            if request.reasoning_level is None or not _is_gemini_model(request.model):
                raise

            logger.warning(
                "Style guide | Draft pack | JSON invalide avec reasoning, retry sans reasoning",
                model=request.model,
                reasoning_level=request.reasoning_level,
            )
            response = await _acompletion(request, self._settings, None)
        except (AuthenticationError, BadRequestError) as exc:
            raise ValueError(f"Erreur LLM non-retryable: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Le LLM a retourne une reponse vide.")

        return LLMCompletionResponse(content=content)


def _normalize_response_format(
    model: str,
    response_format: dict[str, object],
) -> dict[str, object]:
    if not _is_gemini_model(model) or response_format.get("type") != "json_schema":
        return response_format

    json_schema = response_format.get("json_schema")
    if not isinstance(json_schema, dict):
        return response_format

    schema = json_schema.get("schema")
    if not isinstance(schema, dict):
        return response_format

    return {
        "type": "json_object",
        "response_schema": schema,
        "enforce_validation": True,
    }


def _is_gemini_model(model: str) -> bool:
    return model.startswith(("gemini/", "vertex_ai/gemini"))


async def _acompletion(
    request: LLMCompletionRequest,
    settings: Settings,
    reasoning_level: ReasoningLevel | None,
) -> Any:
    optional_params = {
        **_provider_kwargs(request.model, settings),
        **_reasoning_kwargs(request.model, reasoning_level),
    }
    return await litellm.acompletion(
        model=request.model,
        messages=[
            {"role": message.role, "content": message.content} for message in request.messages
        ],
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        timeout=request.timeout_seconds,
        response_format=_normalize_response_format(
            request.model,
            request.response_format,
        ),
        enable_json_schema_validation=True,
        num_retries=0,
        metadata=request.metadata,
        **optional_params,
    )


def _reasoning_kwargs(
    model: str,
    reasoning_level: ReasoningLevel | None,
) -> dict[str, str]:
    if reasoning_level is None or not _supports_openai_param(model, "reasoning_effort"):
        return {}
    return {"reasoning_effort": reasoning_level}


def _supports_openai_param(model: str, param: str) -> bool:
    try:
        supported_params = litellm.get_supported_openai_params(model) or []
        return param in supported_params
    except Exception:
        return False


def _provider_kwargs(model: str, settings: Settings) -> dict[str, str]:
    if not model.startswith("vertex_ai/"):
        return {}

    return {
        key: value
        for key, value in {
            "vertex_project": settings.gcp.project_id,
            "vertex_location": settings.gcp.location,
        }.items()
        if value
    }
