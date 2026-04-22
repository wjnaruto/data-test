from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.error import URLError

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError

from core.config import settings
from db.session import db
from db.repositories.maker_checker import TenantRoleMappingRepository


_jwk_client: Optional[PyJWKClient] = None
_tenant_role_mapping_repository = TenantRoleMappingRepository()
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    user_id: str
    user_name: str
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
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Bearer access token is required.",
        )

    claims = await _resolve_token_claims(credentials.credentials)
    user_id = claims.get(settings.auth_user_id_claim) or claims.get("sub")
    user_name = (
        claims.get(settings.auth_user_name_claim)
        or claims.get("preferred_username")
        or claims.get("name")
        or user_id
    )
    groups = _extract_groups(claims)

    if not user_id:
        raise HTTPException(status_code=401, detail="Authenticated token does not contain user id claim.")

    return AuthenticatedUser(
        user_id=str(user_id),
        user_name=str(user_name or user_id),
        groups=groups,
    )


async def get_current_access_context(
    user: AuthenticatedUser = Security(get_authenticated_user),
) -> UserAccessContext:
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


async def _resolve_token_claims(token: str) -> Dict[str, Any]:
    if not settings.auth_jwks_url:
        raise HTTPException(
            status_code=500,
            detail="Auth server integration is not configured. Set AUTH_JWKS_URL for JWT validation.",
        )
    if not settings.auth_issuer:
        raise HTTPException(
            status_code=500,
            detail="Auth server integration is not configured. Set AUTH_ISSUER for JWT validation.",
        )
    return _decode_jwt_locally(token)


def _decode_jwt_locally(token: str) -> Dict[str, Any]:
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        algorithms = [item.strip() for item in settings.auth_jwt_algorithms.split(",") if item.strip()]
        options = {"verify_aud": bool(settings.auth_audience)}
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=algorithms or ["RS256"],
            audience=settings.auth_audience or None,
            issuer=settings.auth_issuer or None,
            options=options,
        )
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Access token is invalid or expired.")
    except URLError:
        raise HTTPException(status_code=502, detail="Failed to reach auth server JWKS endpoint.")


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(settings.auth_jwks_url)
    return _jwk_client


def _extract_groups(claims: Dict[str, Any]) -> List[str]:
    value = claims.get(settings.auth_groups_claim)

    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []
