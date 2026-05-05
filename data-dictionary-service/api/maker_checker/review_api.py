from fastapi import APIRouter, Depends

from schemas.maker_checker.review import ReviewRequest, ReviewResponse
from services.access_control import UserAccessContext, get_current_access_context
from services.maker_checker.review_service import ReviewService


router = APIRouter()
service = ReviewService()


@router.post(
    "/review/approve",
    response_model=ReviewResponse,
    tags=["Maker Checker"],
    summary="Approve pending dataset and attribute changes",
    description=(
        "Approve selected maker-checker pending rows. The request can include explicit pending item ids, "
        "or request-level selections scoped to the dataset or attribute dashboard tab."
    ),
)
async def approve_changes(
    payload: ReviewRequest,
    access: UserAccessContext = Depends(get_current_access_context),
):
    return await service.approve(payload, access)


@router.post(
    "/review/reject",
    response_model=ReviewResponse,
    tags=["Maker Checker"],
    summary="Reject pending dataset and attribute changes",
    description=(
        "Reject selected maker-checker pending rows. The request can include explicit pending item ids, "
        "or request-level selections scoped to the dataset or attribute dashboard tab."
    ),
)
async def reject_changes(
    payload: ReviewRequest,
    access: UserAccessContext = Depends(get_current_access_context),
):
    return await service.reject(payload, access)
