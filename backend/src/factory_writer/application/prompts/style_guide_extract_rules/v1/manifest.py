from .output_schema import STYLE_PACK_CANDIDATE_RESPONSE_FORMAT

SYSTEM_TEMPLATE_FILE = "system.mustache"
USER_TEMPLATE_FILE = "user.mustache"

# Equivalent local de prompt.config Langfuse.
LLM_CONFIG = {
    "model": "vertex_ai/gemini-3-pro-preview",
    "temperature": 0.0,
    "max_tokens": 4096,
    "response_format": STYLE_PACK_CANDIDATE_RESPONSE_FORMAT,
}
