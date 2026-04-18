import litellm
from litellm.exceptions import AuthenticationError, BadRequestError

from factory_writer.application.ports import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    LLMGatewayPort,
)
from factory_writer.core.config import Settings


class LiteLLMGateway(LLMGatewayPort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def complete(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        try:
            response = await litellm.acompletion(
                model=request.model,
                messages=[
                    {"role": message.role, "content": message.content}
                    for message in request.messages
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
                **_provider_kwargs(request.model, self._settings),
            )
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
