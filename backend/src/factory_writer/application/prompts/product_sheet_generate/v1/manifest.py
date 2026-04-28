from .output_schema import PRODUCT_SHEET_CANDIDATE_RESPONSE_FORMAT

SYSTEM_TEMPLATE_FILE = "system.mustache"
USER_TEMPLATE_FILE = "user.mustache"

LLM_CONFIG = {
    "model": "vertex_ai/gemini-3-flash-preview",
    "temperature": 0.2,
    "max_tokens": 6144,
    "reasoning_level": "minimal",
    "response_format": PRODUCT_SHEET_CANDIDATE_RESPONSE_FORMAT,
}
