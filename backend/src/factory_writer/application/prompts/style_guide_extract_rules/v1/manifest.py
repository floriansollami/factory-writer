from .output_schema import STYLE_PACK_CANDIDATE_RESPONSE_FORMAT

SYSTEM_TEMPLATE_FILE = "system.mustache"
USER_TEMPLATE_FILE = "user.mustache"

# Equivalent local de prompt.config Langfuse.
LLM_CONFIG = {
    "model": "vertex_ai/gemini-3.1-pro-preview",
    "temperature": 1.0,
    "max_tokens": 12288,
    "reasoning_level": "high",
    "response_format": STYLE_PACK_CANDIDATE_RESPONSE_FORMAT,
}
