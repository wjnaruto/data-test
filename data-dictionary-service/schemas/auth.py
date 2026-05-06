from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username entered by the user.")
    password: str = Field(..., description="Password entered by the user.")


class TenantRoleResponse(BaseModel):
    domainId: str = Field(..., description="Domain id associated with the role mapping.")
    tenantUniqueId: str = Field(..., description="Tenant id associated with the role mapping.")
    roleType: str = Field(..., description="Data Dictionary role resolved from tenant role mapping.")
    adGroupName: str = Field(..., description="AD group name matched from the session authorities.")


class AuthMeResponse(BaseModel):
    authenticated: bool = Field(True, description="Whether a valid Data Dictionary session exists.")
    userId: Optional[str] = Field(default=None, description="Authenticated user id.")
    userName: Optional[str] = Field(default=None, description="Authenticated username.")
    displayName: Optional[str] = Field(default=None, description="Authenticated user display name.")
    email: Optional[str] = Field(default=None, description="Authenticated user email.")
    groups: list[str] = Field(default_factory=list, description="Authorities resolved from the active session.")
    roles: list[TenantRoleResponse] = Field(
        default_factory=list,
        description="Data Dictionary roles resolved from active tenant role mappings.",
    )


class LoginResponse(AuthMeResponse):
    pass


class LogoutResponse(BaseModel):
    success: bool = Field(True, description="Whether the logout request completed.")
