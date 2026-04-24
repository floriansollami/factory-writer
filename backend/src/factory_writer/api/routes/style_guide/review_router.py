import uuid

from fastapi import APIRouter, Depends, HTTPException, Response

from factory_writer.api.routes.style_guide.dependencies import (
    STYLE_GUIDE_TAG,
    get_style_guide_admin_action_service,
)
from factory_writer.api.routes.style_guide.schemas import StyleGuideRulePatchRequest
from factory_writer.application.services.style_guide_admin_service import (
    StyleGuideAdminService,
)

router = APIRouter()


@router.patch(
    "/packs/{style_pack_id}/rules/{rule_id}",
    status_code=204,
    tags=[STYLE_GUIDE_TAG],
)
async def patch_style_guide_rule(
    style_pack_id: uuid.UUID,
    rule_id: uuid.UUID,
    request: StyleGuideRulePatchRequest,
    service: StyleGuideAdminService = Depends(get_style_guide_admin_action_service),
) -> Response:
    try:
        await service.patch_rule(
            style_pack_id=style_pack_id,
            rule_id=rule_id,
            texte_regle=request.texteRegle if "texteRegle" in request.model_fields_set else None,
            type_regle=request.typeRegle if "typeRegle" in request.model_fields_set else None,
            niveau_contrainte=(
                request.niveauContrainte if "niveauContrainte" in request.model_fields_set else None
            ),
            taxonomie_code=(
                request.taxonomieCode if "taxonomieCode" in request.model_fields_set else None
            ),
            decision_editoriale=(
                request.decisionEditoriale
                if "decisionEditoriale" in request.model_fields_set
                else None
            ),
            est_actif=request.estActif if "estActif" in request.model_fields_set else None,
            commentaire_review=(
                request.commentaire if "commentaire" in request.model_fields_set else None
            ),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Règle ou pack introuvable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return Response(status_code=204)


@router.post(
    "/packs/{style_pack_id}/approve",
    status_code=200,
    tags=[STYLE_GUIDE_TAG],
)
async def approve_style_guide_pack(
    style_pack_id: uuid.UUID,
    service: StyleGuideAdminService = Depends(get_style_guide_admin_action_service),
) -> dict[str, str]:
    try:
        await service.approve_style_pack(style_pack_id=style_pack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Pack style guide introuvable.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "status": "completed",
        "stylePackId": str(style_pack_id),
    }


@router.post(
    "/packs/{style_pack_id}/reject",
    status_code=200,
    tags=[STYLE_GUIDE_TAG],
)
async def reject_style_guide_pack(
    style_pack_id: uuid.UUID,
    service: StyleGuideAdminService = Depends(get_style_guide_admin_action_service),
) -> dict[str, str]:
    try:
        await service.reject_style_pack(style_pack_id=style_pack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Pack style guide introuvable.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "status": "rejected",
        "stylePackId": str(style_pack_id),
    }
