from fastapi import APIRouter, Depends

from schemas.auth import AuthMeResponse
from services.access_control import AuthenticatedUser, get_authenticated_user


router = APIRouter()


@router.get(
    "/auth/me",
    response_model=AuthMeResponse,
    tags=["Authentication"],
    summary="Get authenticated user from bearer token",
    description=(
        "Validate the JWT bearer access token using JWKS and return the resolved user identity and groups claim."
    ),
)
async def get_auth_me(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> AuthMeResponse:
    return AuthMeResponse(
        userId=user.user_id,
        userName=user.user_name,
        groups=user.groups,
    )
