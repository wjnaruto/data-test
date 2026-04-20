from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.maker_checker import TenantRoleMapping


class TenantRoleMappingRepository:

    async def get_active_mapping(
        self,
        session: AsyncSession,
        tenant_unique_id: str,
        role_type: str,
    ) -> Optional[TenantRoleMapping]:
        statement = (
            select(TenantRoleMapping)
            .where(TenantRoleMapping.tenant_unique_id == tenant_unique_id)
            .where(TenantRoleMapping.role_type == role_type)
            .where(TenantRoleMapping.is_active.is_(True))
            .limit(1)
        )
        result = await session.execute(statement)
        return result.scalars().first()
