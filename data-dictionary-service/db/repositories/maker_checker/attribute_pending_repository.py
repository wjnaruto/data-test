from __future__ import annotations

from typing import Any, Dict, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.maker_checker import AttributeEntityPending


class AttributePendingRepository:

    async def find_pending_conflict_by_target_id(
        self,
        session: AsyncSession,
        target_attribute_id: str,
    ):
        statement = (
            sa.select(
                AttributeEntityPending.__table__.c.pending_id,
                AttributeEntityPending.__table__.c.request_id,
            )
            .where(AttributeEntityPending.__table__.c.target_attribute_id == target_attribute_id)
            .where(AttributeEntityPending.__table__.c.approval_status == "P")
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()

    async def find_pending_conflict_by_business_key(
        self,
        session: AsyncSession,
        table_id: str,
        tenant_unique_id: str,
        field_name: str,
    ):
        statement = (
            sa.select(
                AttributeEntityPending.__table__.c.pending_id,
                AttributeEntityPending.__table__.c.request_id,
            )
            .where(AttributeEntityPending.__table__.c.approval_status == "P")
            .where(AttributeEntityPending.__table__.c.table_id == table_id)
            .where(AttributeEntityPending.__table__.c.tenant_unique_id == tenant_unique_id)
            .where(sa.func.lower(AttributeEntityPending.__table__.c.field_name) == field_name.lower())
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()

    async def create_pending(
        self,
        session: AsyncSession,
        pending_id: str,
        request_id: str,
        target_attribute_id: Optional[str],
        metadata_json: Dict[str, Any],
        dictionary_action: str,
        current_version_seq: Optional[int],
        target_version_seq: Optional[int],
        requester_id: str,
        maker_comment: Optional[str],
        current_snapshot: Optional[Dict[str, Any]],
    ) -> None:
        statement = sa.insert(AttributeEntityPending.__table__).values(
            {
                "pending_id": pending_id,
                "request_id": request_id,
                "target_attribute_id": target_attribute_id,
                "metadata": metadata_json,
                "dictionary_action": dictionary_action,
                "approval_status": "P",
                "current_version_seq": current_version_seq,
                "target_version_seq": target_version_seq,
                "requester_id": requester_id,
                "maker_comment": maker_comment,
                "current_snapshot": current_snapshot,
            }
        )

        await session.execute(statement)
