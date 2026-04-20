from pydantic import BaseModel, Field


class AuthMeResponse(BaseModel):
    authenticated: bool = Field(True, description="Whether the bearer token is valid.")
    userId: str = Field(..., description="Authenticated user id resolved from JWT claims.")
    userName: str = Field(..., description="Authenticated user display name resolved from JWT claims.")
    groups: list[str] = Field(default_factory=list, description="Groups claim resolved from JWT access token.")
