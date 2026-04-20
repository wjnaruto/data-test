from __future__ import annotations

from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


ALEMBIC_TRACKED_TABLES = {
    "approval_request",
    "tenant_role_mapping",
    "table_entity_pending",
    "attribute_entity_pending",
    "table_entity_history",
    "attribute_entity_history",
}


sa.Table(
    "domain_entity",
    SQLModel.metadata,
    sa.Column("id", sa.String(length=36), primary_key=True),
    extend_existing=True,
)
sa.Table(
    "tenant_entity",
    SQLModel.metadata,
    sa.Column("id", sa.String(length=36), primary_key=True),
    extend_existing=True,
)
sa.Table(
    "table_entity",
    SQLModel.metadata,
    sa.Column("id", sa.String(length=36), primary_key=True),
    extend_existing=True,
)
sa.Table(
    "attribute_entity",
    SQLModel.metadata,
    sa.Column("id", sa.String(length=36), primary_key=True),
    extend_existing=True,
)

