from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.auth import UserSession


class UserSessionRepository:

    async def create(self, session: AsyncSession, user_session: UserSession) -> UserSession:
        session.add(user_session)
        await session.flush()
        return user_session

    async def get_active(
        self,
        session: AsyncSession,
        session_id_hash: str,
        now: datetime,
    ) -> Optional[UserSession]:
        statement = (
            select(UserSession)
            .where(UserSession.session_id_hash == session_id_hash)
            .where(UserSession.expires_at > now)
            .where(UserSession.revoked_at.is_(None))
            .limit(1)
        )
        result = await session.execute(statement)
        return result.scalars().first()

    async def touch(self, session: AsyncSession, session_id_hash: str, now: datetime) -> None:
        statement = (
            update(UserSession)
            .where(UserSession.session_id_hash == session_id_hash)
            .values(last_seen_at=now)
        )
        await session.execute(statement)

    async def revoke(self, session: AsyncSession, session_id_hash: str, now: datetime) -> None:
        statement = (
            update(UserSession)
            .where(UserSession.session_id_hash == session_id_hash)
            .where(UserSession.revoked_at.is_(None))
            .values(revoked_at=now, last_seen_at=now)
        )
        await session.execute(statement)
