from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession


domain_entity = sa.table(
    "domain_entity",
    sa.column("id", sa.String(length=36)),
    sa.column("name", sa.String(length=256)),
    sa.column("metadata", JSONB),
)

tenant_entity = sa.table(
    "tenant_entity",
    sa.column("id", sa.String(length=36)),
    sa.column("name", sa.String(length=256)),
    sa.column("metadata", JSONB),
    sa.column("domain_id", sa.String(length=36)),
)


class ReferenceDataRepository:

    async def get_domain_by_id(self, session: AsyncSession, domain_id: str):
        statement = (
            sa.select(
                domain_entity.c.id,
                domain_entity.c.name,
                domain_entity.c.metadata,
            )
            .where(domain_entity.c.id == domain_id)
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()

    async def get_tenant_by_id(self, session: AsyncSession, tenant_unique_id: str):
        statement = (
            sa.select(
                tenant_entity.c.id,
                tenant_entity.c.name,
                tenant_entity.c.metadata,
                tenant_entity.c.domain_id,
            )
            .where(tenant_entity.c.id == tenant_unique_id)
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()
