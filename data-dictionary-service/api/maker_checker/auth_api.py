from fastapi import APIRouter, Depends

from schemas.auth import AuthMeResponse, TenantRoleResponse
from services.access_control import UserAccessContext, get_current_access_context


router = APIRouter()


@router.get(
    "/auth/me",
    response_model=AuthMeResponse,
    tags=["Authentication"],
    summary="Get authenticated user from bearer token",
    description=(
        "Validate the JWT bearer access token using JWKS and return the resolved user identity, "
        "groups claim, and Data Dictionary tenant roles."
    ),
)
async def get_auth_me(
    access: UserAccessContext = Depends(get_current_access_context),
) -> AuthMeResponse:
    return AuthMeResponse(
        userId=access.user_id,
        userName=access.user_name,
        groups=access.groups,
        roles=[
            TenantRoleResponse(
                domainId=role.domain_id,
                tenantUniqueId=role.tenant_unique_id,
                roleType=role.role_type,
                adGroupName=role.ad_group_name,
            )
            for role in access.roles
        ],
    )
