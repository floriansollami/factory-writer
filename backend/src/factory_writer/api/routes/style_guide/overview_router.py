from fastapi import APIRouter, Depends

from factory_writer.api.routes.style_guide.dependencies import (
    STYLE_GUIDE_TAG,
    get_style_guide_admin_read_service,
)
from factory_writer.api.routes.style_guide.mappers import to_overview_response
from factory_writer.application.services.style_guide_admin_service import (
    StyleGuideAdminService,
)

router = APIRouter()


@router.get("/overview", tags=[STYLE_GUIDE_TAG])
async def get_style_guide_overview(
    service: StyleGuideAdminService = Depends(get_style_guide_admin_read_service),
) -> dict[str, object]:
    overview = await service.get_overview()
    return to_overview_response(overview)
