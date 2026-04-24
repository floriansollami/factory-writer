from factory_writer.infrastructure.llm.litellm_gateway import _reasoning_kwargs
from factory_writer.infrastructure.prompts.local_prompt_registry import (
    _reasoning_level_from_manifest,
)


def test_reasoning_level_is_passed_through_as_litellm_reasoning_effort() -> None:
    assert _reasoning_kwargs("vertex_ai/gemini-3.1-pro-preview", "high") == {
        "reasoning_effort": "high"
    }


def test_reasoning_kwargs_are_omitted_for_unmapped_provider() -> None:
    assert _reasoning_kwargs("anthropic/claude-sonnet-4", "high") == {}


def test_manifest_prefers_generic_reasoning_level() -> None:
    assert _reasoning_level_from_manifest({"reasoning_level": "high"}) == "high"


def test_manifest_keeps_legacy_reasoning_effort_compatible() -> None:
    assert _reasoning_level_from_manifest({"reasoning_effort": "xhigh"}) == "high"
