from fastapi import APIRouter, Depends

from schemas.maker_checker.submit import SubmitRequest, SubmitResponse
from services.access_control import UserAccessContext, get_current_access_context
from services.maker_checker.submit_service import SubmitService


router = APIRouter()
service = SubmitService()


@router.post(
    "/submit",
    response_model=SubmitResponse,
    tags=["Maker Checker"],
    summary="Submit dataset and attribute changes for approval",
    description=(
        "Stage dataset and attribute add/update/delete changes into maker-checker pending tables. "
        "This endpoint requires an active Data Dictionary session cookie and requester role validation for the target tenant."
    ),
)
async def submit_changes(
    payload: SubmitRequest,
    access: UserAccessContext = Depends(get_current_access_context),
):
    return await service.submit(payload, access)
