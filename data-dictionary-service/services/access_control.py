from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Cookie, Depends, HTTPException

from core.config import settings
from db.repositories.auth import UserSessionRepository
from db.repositories.maker_checker import TenantRoleMappingRepository
from db.session import db
from services.auth_session_service import hash_session_id


_tenant_role_mapping_repository = TenantRoleMappingRepository()
_user_session_repository = UserSessionRepository()


@dataclass
class AuthenticatedUser:
    user_id: str
    user_name: str
    display_name: Optional[str]
    email: Optional[str]
    groups: List[str]


@dataclass
class TenantRole:
    domain_id: str
    tenant_unique_id: str
    role_type: str
    ad_group_name: str


@dataclass
class UserAccessContext:
    user_id: str
    user_name: str
    display_name: Optional[str]
    email: Optional[str]
    groups: List[str]
    roles: List[TenantRole]

    def has_role(self, tenant_unique_id: str, role_type: str) -> bool:
        expected_role = role_type.upper()
        return any(
            role.tenant_unique_id == tenant_unique_id and role.role_type == expected_role
            for role in self.roles
        )

    def require_role(self, tenant_unique_id: str, role_type: str) -> None:
        expected_role = role_type.upper()
        if not self.has_role(tenant_unique_id, expected_role):
            raise HTTPException(
                status_code=403,
                detail=f"User does not have {expected_role} role for tenant {tenant_unique_id}.",
            )

    def require_requester(self, tenant_unique_id: str) -> None:
        self.require_role(tenant_unique_id, "REQUESTER")

    def require_approver(self, tenant_unique_id: str) -> None:
        self.require_role(tenant_unique_id, "APPROVER")


async def get_authenticated_user(
    session_id: Optional[str] = Cookie(default=None, alias=settings.session_cookie_name),
) -> AuthenticatedUser:
    if not session_id:
        raise HTTPException(status_code=401, detail="Active session cookie is required.")

    user = await get_optional_authenticated_user(session_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Session is invalid or expired.")
    return user


async def get_optional_authenticated_user(
    session_id: Optional[str] = Cookie(default=None, alias=settings.session_cookie_name),
) -> Optional[AuthenticatedUser]:
    if not session_id:
        return None
    if db.engine is None:
        raise HTTPException(status_code=500, detail="Database engine is not initialized.")

    now = datetime.now(timezone.utc)
    async with db.session() as session:
        user_session = await _user_session_repository.get_active(
            session=session,
            session_id_hash=hash_session_id(session_id),
            now=now,
        )
        if user_session is None:
            return None
        await _user_session_repository.touch(session, user_session.session_id_hash, now)
        await session.commit()

    return AuthenticatedUser(
        user_id=user_session.username,
        user_name=user_session.display_name or user_session.username,
        display_name=user_session.display_name,
        email=user_session.email,
        groups=_extract_groups(user_session.authorities),
    )


async def get_current_access_context(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> UserAccessContext:
    return await build_access_context(user)


async def get_optional_access_context(
    user: Optional[AuthenticatedUser] = Depends(get_optional_authenticated_user),
) -> Optional[UserAccessContext]:
    if user is None:
        return None
    return await build_access_context(user)


async def build_access_context(user: AuthenticatedUser) -> UserAccessContext:
    if db.engine is None:
        raise HTTPException(status_code=500, detail="Database engine is not initialized.")

    async with db.session() as session:
        mappings = await _tenant_role_mapping_repository.get_active_mappings_for_groups(
            session=session,
            groups=user.groups,
        )

    return UserAccessContext(
        user_id=user.user_id,
        user_name=user.user_name,
        display_name=user.display_name,
        email=user.email,
        groups=user.groups,
        roles=[
            TenantRole(
                domain_id=mapping.domain_id,
                tenant_unique_id=mapping.tenant_unique_id,
                role_type=mapping.role_type,
                ad_group_name=mapping.ad_group_name,
            )
            for mapping in mappings
        ],
    )


def _extract_groups(authorities: object) -> List[str]:
    if authorities is None:
        return []
    if isinstance(authorities, list):
        return [str(item).strip() for item in authorities if str(item).strip()]
    if isinstance(authorities, str):
        return [item.strip() for item in authorities.split(",") if item.strip()]
    return []
