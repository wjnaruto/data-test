from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession


table_entity = sa.table(
    "table_entity",
    sa.column("id", sa.String(length=36)),
    sa.column("table_metadata", JSONB),
    sa.column("version_seq", sa.Integer()),
    sa.column("domain_id", sa.String(length=36)),
    sa.column("tenant_unique_id", sa.String(length=36)),
    sa.column("record_status", sa.CHAR(length=1)),
)


class TableEntityRepository:

    async def get_by_id(self, session: AsyncSession, table_id: str):
        statement = (
            sa.select(
                table_entity.c.id,
                table_entity.c.table_metadata,
                table_entity.c.version_seq,
                table_entity.c.domain_id,
                table_entity.c.tenant_unique_id,
                table_entity.c.record_status,
            )
            .where(table_entity.c.id == table_id)
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()
