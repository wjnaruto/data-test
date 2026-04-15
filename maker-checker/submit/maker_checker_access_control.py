from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib import parse, request
from urllib.error import HTTPError, URLError

from fastapi import Header, HTTPException
import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError

from core.config import settings


_jwk_client: Optional[PyJWKClient] = None


@dataclass
class AuthenticatedUser:
    user_id: str
    user_name: str
    groups: List[str]


async def get_authenticated_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Bearer access token is required for submit.",
        )

    token = authorization[len("Bearer ") :].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer access token is required for submit.")

    claims = await _resolve_token_claims(token)
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


async def validate_requester_tenant_access(connection, tenant_unique_id: str, user: AuthenticatedUser) -> None:
    query = """
        SELECT mapping_id, ad_group_name
        FROM tenant_role_mapping
        WHERE tenant_unique_id = $1
          AND role_type = 'REQUESTER'
          AND is_active = true
        LIMIT 1
    """
    mapping = await connection.fetchrow(query, tenant_unique_id)

    if mapping is None:
        raise HTTPException(
            status_code=403,
            detail=f"No active requester role mapping found for tenant {tenant_unique_id}.",
        )

    if mapping["ad_group_name"] not in user.groups:
        raise HTTPException(
            status_code=403,
            detail=f"User does not belong to the requester AD group for tenant {tenant_unique_id}.",
        )


async def _resolve_token_claims(token: str) -> Dict[str, Any]:
    if settings.auth_jwks_url:
        return await asyncio.to_thread(_decode_jwt_locally, token)
    if settings.auth_userinfo_url:
        return await asyncio.to_thread(_call_userinfo_endpoint, token)
    if settings.auth_introspection_url:
        return await asyncio.to_thread(_call_introspection_endpoint, token)

    raise HTTPException(
        status_code=500,
        detail=(
            "Auth server integration is not configured. "
            "Set AUTH_JWKS_URL for JWT validation, or AUTH_USERINFO_URL / AUTH_INTROSPECTION_URL."
        ),
    )


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


def _call_userinfo_endpoint(token: str) -> Dict[str, Any]:
    req = request.Request(
        settings.auth_userinfo_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise HTTPException(status_code=401, detail="Access token is invalid or expired.")
        raise HTTPException(status_code=502, detail="Auth server userinfo endpoint returned an error.")
    except URLError:
        raise HTTPException(status_code=502, detail="Failed to reach auth server userinfo endpoint.")


def _call_introspection_endpoint(token: str) -> Dict[str, Any]:
    body = parse.urlencode({"token": token}).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    if settings.auth_client_id:
        basic = base64.b64encode(
            f"{settings.auth_client_id}:{settings.auth_client_secret}".encode("utf-8")
        ).decode("utf-8")
        headers["Authorization"] = f"Basic {basic}"

    req = request.Request(
        settings.auth_introspection_url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise HTTPException(status_code=401, detail="Access token is invalid or expired.")
        raise HTTPException(status_code=502, detail="Auth server introspection endpoint returned an error.")
    except URLError:
        raise HTTPException(status_code=502, detail="Failed to reach auth server introspection endpoint.")

    if not payload.get("active"):
        raise HTTPException(status_code=401, detail="Access token is invalid or expired.")

    return payload


def _extract_groups(claims: Dict[str, Any]) -> List[str]:
    value = claims.get(settings.auth_groups_claim)
    if value is None:
        value = claims.get("groups")
    if value is None:
        value = claims.get("roles")
    if value is None:
        value = claims.get("authorities")

    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []
