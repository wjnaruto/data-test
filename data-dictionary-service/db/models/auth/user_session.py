from __future__ import annotations

from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class UserSession(SQLModel, table=True):
    __tablename__ = "user_session"
    __table_args__ = (
        sa.Index("user_session_username_idx", "username"),
        sa.Index("user_session_expires_at_idx", "expires_at"),
    )

    session_id_hash: str = Field(primary_key=True, max_length=128, description="SHA-256 hash of the opaque session id stored in the browser cookie.")
    username: str = Field(max_length=256, description="Authenticated username returned by the OAuth server.")
    display_name: Optional[str] = Field(default=None, max_length=256, description="Human-readable display name returned by the OAuth server.")
    email: Optional[str] = Field(default=None, max_length=512, description="Authenticated user's email address returned by the OAuth server.")
    authorities: list[str] = Field(
        default_factory=list,
        sa_column=sa.Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        description="Authority or AD group names returned by the OAuth server for this session.",
    )
    created_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        description="Timestamp when the session record was created.",
    )
    expires_at: Any = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False), description="Timestamp after which the session is no longer valid.")
    last_seen_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True), description="Timestamp when the session was last used by an API request.")
    revoked_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True), description="Timestamp when the session was explicitly revoked by logout or administration.")
