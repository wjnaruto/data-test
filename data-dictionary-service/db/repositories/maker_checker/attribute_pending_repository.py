from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

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

    async def get_by_ids_for_update(self, session: AsyncSession, pending_ids: Iterable[str]):
        ids = list(pending_ids)
        if not ids:
            return []
        statement = (
            sa.select(AttributeEntityPending.__table__)
            .where(AttributeEntityPending.__table__.c.pending_id.in_(ids))
            .with_for_update()
        )
        result = await session.execute(statement)
        return result.mappings().all()

    async def get_pending_by_request_for_update(self, session: AsyncSession, request_id: str):
        statement = (
            sa.select(AttributeEntityPending.__table__)
            .where(AttributeEntityPending.__table__.c.request_id == request_id)
            .where(AttributeEntityPending.__table__.c.approval_status == "P")
            .with_for_update()
        )
        result = await session.execute(statement)
        return result.mappings().all()

    async def find_pending_by_table_ids(self, session: AsyncSession, table_ids: Iterable[str]):
        ids = list({table_id for table_id in table_ids if table_id})
        if not ids:
            return []
        statement = (
            sa.select(AttributeEntityPending.__table__)
            .where(AttributeEntityPending.__table__.c.table_id.in_(ids))
            .where(AttributeEntityPending.__table__.c.approval_status == "P")
        )
        result = await session.execute(statement)
        return result.mappings().all()

    async def mark_reviewed(
        self,
        session: AsyncSession,
        pending_ids: Iterable[str],
        approval_status: str,
        approver_id: str,
        approver_ts,
        checker_comment: Optional[str],
    ) -> None:
        ids = list(pending_ids)
        if not ids:
            return
        statement = (
            sa.update(AttributeEntityPending.__table__)
            .where(AttributeEntityPending.__table__.c.pending_id.in_(ids))
            .values(
                approval_status=approval_status,
                approver_id=approver_id,
                approver_ts=approver_ts,
                checker_comment=checker_comment,
                updated_at=approver_ts,
            )
        )
        await session.execute(statement)

    async def count_status_by_request(self, session: AsyncSession, request_id: str):
        statement = (
            sa.select(
                AttributeEntityPending.__table__.c.approval_status,
                sa.func.count().label("item_count"),
            )
            .where(AttributeEntityPending.__table__.c.request_id == request_id)
            .group_by(AttributeEntityPending.__table__.c.approval_status)
        )
        result = await session.execute(statement)
        return result.mappings().all()
