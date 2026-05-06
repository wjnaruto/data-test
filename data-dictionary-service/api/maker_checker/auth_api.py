from fastapi import APIRouter, Cookie, Depends, Response

from core.config import settings
from schemas.auth import AuthMeResponse, LoginRequest, LoginResponse, LogoutResponse, TenantRoleResponse
from services.access_control import AuthenticatedUser, UserAccessContext, build_access_context, get_optional_access_context
from services.auth_session_service import AuthSessionService


router = APIRouter()
service = AuthSessionService()


def _to_auth_response(access: UserAccessContext | None) -> AuthMeResponse:
    if access is None:
        return AuthMeResponse(authenticated=False)

    return AuthMeResponse(
        authenticated=True,
        userId=access.user_id,
        userName=access.user_id,
        displayName=access.display_name or access.user_name,
        email=access.email,
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


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    tags=["Authentication"],
    summary="Login with username and password",
    description=(
        "Authenticate the user via the configured OAuth server login endpoint, "
        "create a Data Dictionary server-side session, and return it as an HttpOnly cookie."
    ),
)
async def login(payload: LoginRequest, response: Response) -> LoginResponse:
    user_info = await service.login(payload.username, payload.password, response)
    access = await build_access_context(
        AuthenticatedUser(
            user_id=user_info.username,
            user_name=user_info.display_name or user_info.username,
            display_name=user_info.display_name,
            email=user_info.email,
            groups=user_info.authorities,
        )
    )
    return LoginResponse(**_to_auth_response(access).model_dump())


@router.get(
    "/auth/me",
    response_model=AuthMeResponse,
    tags=["Authentication"],
    summary="Get current session user",
    description="Return the user, authorities, and Data Dictionary tenant roles resolved from the session cookie.",
)
async def get_auth_me(
    access: UserAccessContext | None = Depends(get_optional_access_context),
) -> AuthMeResponse:
    return _to_auth_response(access)


@router.post(
    "/auth/logout",
    response_model=LogoutResponse,
    tags=["Authentication"],
    summary="Logout current session",
    description="Revoke the current Data Dictionary session and clear the session cookie.",
)
async def logout(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> LogoutResponse:
    await service.logout(session_id, response)
    return LogoutResponse(success=True)
