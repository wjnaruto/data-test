from fastapi import APIRouter, Depends

from models.submit_models import SubmitRequest, SubmitResponse
from services.maker_checker_access_control import get_authenticated_user
from services.submit_impl import SubmitService


router = APIRouter()
service = SubmitService()


@router.post(
    "/submit",
    response_model=SubmitResponse,
    tags=["Maker Checker"],
    summary="Submit dataset and attribute changes for approval",
    description=(
        "Stage dataset and attribute add/update/delete changes into maker-checker pending tables. "
        "This endpoint requires OAuth2 Bearer token validation and requester role validation for the target tenant."
    ),
)
async def submit_changes(
    payload: SubmitRequest,
    user=Depends(get_authenticated_user),
):
    return await service.submit(payload, user)
