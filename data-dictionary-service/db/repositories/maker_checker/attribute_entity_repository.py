from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession


attribute_entity = sa.table(
    "attribute_entity",
    sa.column("id", sa.String(length=36)),
    sa.column("metadata", JSONB),
    sa.column("version_seq", sa.Integer()),
    sa.column("domain_id", sa.String(length=36)),
    sa.column("tenant_unique_id", sa.String(length=36)),
    sa.column("table_id", sa.String(length=36)),
    sa.column("record_status", sa.CHAR(length=1)),
)


class AttributeEntityRepository:

    async def get_by_id(self, session: AsyncSession, attribute_id: str):
        statement = (
            sa.select(
                attribute_entity.c.id,
                attribute_entity.c.metadata,
                attribute_entity.c.version_seq,
                attribute_entity.c.domain_id,
                attribute_entity.c.tenant_unique_id,
                attribute_entity.c.table_id,
                attribute_entity.c.record_status,
            )
            .where(attribute_entity.c.id == attribute_id)
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()

    async def get_active_by_table_id(self, session: AsyncSession, table_id: str):
        statement = (
            sa.select(
                attribute_entity.c.id,
                attribute_entity.c.metadata,
                attribute_entity.c.version_seq,
                attribute_entity.c.domain_id,
                attribute_entity.c.tenant_unique_id,
                attribute_entity.c.table_id,
                attribute_entity.c.record_status,
            )
            .where(attribute_entity.c.table_id == table_id)
            .where(sa.func.coalesce(attribute_entity.c.record_status, "A") == "A")
        )
        result = await session.execute(statement)
        return result.mappings().all()
