from pydantic import BaseModel, Field


class TenantRoleResponse(BaseModel):
    domainId: str = Field(..., description="Domain id associated with the role mapping.")
    tenantUniqueId: str = Field(..., description="Tenant id associated with the role mapping.")
    roleType: str = Field(..., description="Data Dictionary role resolved from tenant role mapping.")
    adGroupName: str = Field(..., description="AD group name matched from the JWT groups claim.")


class AuthMeResponse(BaseModel):
    authenticated: bool = Field(True, description="Whether the bearer token is valid.")
    userId: str = Field(..., description="Authenticated user id resolved from JWT claims.")
    userName: str = Field(..., description="Authenticated user display name resolved from JWT claims.")
    groups: list[str] = Field(default_factory=list, description="Groups claim resolved from JWT access token.")
    roles: list[TenantRoleResponse] = Field(
        default_factory=list,
        description="Data Dictionary roles resolved from active tenant role mappings.",
    )
