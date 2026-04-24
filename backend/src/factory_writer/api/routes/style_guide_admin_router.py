from factory_writer.api.routes.style_guide import router
from factory_writer.core.config import get_settings

settings = get_settings()

__all__ = ["router", "settings"]
