from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, Response

from core.config import settings
from db.models.auth import UserSession
from db.repositories.auth import UserSessionRepository
from db.session import db


@dataclass
class OAuthUserInfo:
    username: str
    display_name: Optional[str]
    email: Optional[str]
    authorities: List[str]


class AuthSessionService:

    def __init__(self) -> None:
        self.session_repository = UserSessionRepository()

    async def login(self, username: str, password: str, response: Response) -> OAuthUserInfo:
        user_info = await self._authenticate_with_oauth_server(username, password)
        raw_session_id = secrets.token_urlsafe(48)
        session_id_hash = hash_session_id(raw_session_id)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=settings.session_ttl_seconds)

        if db.engine is None:
            raise HTTPException(status_code=500, detail="Database engine is not initialized.")

        async with db.session() as session:
            async with session.begin():
                await self.session_repository.create(
                    session,
                    UserSession(
                        session_id_hash=session_id_hash,
                        username=user_info.username,
                        display_name=user_info.display_name,
                        email=user_info.email,
                        authorities=user_info.authorities,
                        expires_at=expires_at,
                        last_seen_at=now,
                    ),
                )

        set_session_cookie(response, raw_session_id)
        return user_info

    async def logout(self, session_id: Optional[str], response: Response) -> None:
        if session_id and db.engine is not None:
            now = datetime.now(timezone.utc)
            async with db.session() as session:
                async with session.begin():
                    await self.session_repository.revoke(session, hash_session_id(session_id), now)
        clear_session_cookie(response)

    async def _authenticate_with_oauth_server(self, username: str, password: str) -> OAuthUserInfo:
        if not settings.auth_login_url:
            raise HTTPException(status_code=500, detail="Auth login URL is not configured.")

        payload = {"username": username, "password": password}
        try:
            data = await asyncio.to_thread(_post_json, settings.auth_login_url, payload)
        except HTTPError as exc:
            if exc.code in (400, 401, 403):
                raise HTTPException(status_code=401, detail="Invalid username or password.")
            raise HTTPException(status_code=502, detail=f"Auth server login failed with status {exc.code}.")
        except URLError:
            raise HTTPException(status_code=502, detail="Failed to reach auth server login endpoint.")

        resolved_username = data.get("username") or data.get("userName") or username
        if not resolved_username:
            raise HTTPException(status_code=502, detail="Auth server response does not contain username.")

        return OAuthUserInfo(
            username=str(resolved_username),
            display_name=data.get("displayName") or data.get("display_name") or data.get("name"),
            email=data.get("email"),
            authorities=_extract_authorities(data),
        )


def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=15) as response:
        response_body = response.read().decode("utf-8")
    if not response_body:
        return {}
    return json.loads(response_body)


def _extract_authorities(data: Dict[str, Any]) -> List[str]:
    value = data.get("authorities") or data.get("groups") or []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def hash_session_id(session_id: str) -> str:
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain or None,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        domain=settings.session_cookie_domain or None,
        path="/",
        samesite=settings.session_cookie_samesite,
        secure=settings.session_cookie_secure,
        httponly=True,
    )
