from __future__ import annotations

from typing import Any, Dict, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.maker_checker import AttributeEntityHistory


attribute_entity = sa.table(
    "attribute_entity",
    sa.column("id", sa.String(length=36)),
    sa.column("metadata", JSONB),
    sa.column("version_seq", sa.Integer()),
    sa.column("domain_id", sa.String(length=36)),
    sa.column("tenant_unique_id", sa.String(length=36)),
    sa.column("table_id", sa.String(length=36)),
    sa.column("record_status", sa.CHAR(length=1)),
    sa.column("requester_id", sa.String(length=32)),
    sa.column("approver_id", sa.String(length=32)),
    sa.column("requester_ts", sa.DateTime(timezone=True)),
    sa.column("approver_ts", sa.DateTime(timezone=True)),
    sa.column("dictionary_action", sa.CHAR(length=1)),
    sa.column("approval_status", sa.CHAR(length=1)),
    sa.column("effective_from", sa.DateTime(timezone=True)),
    sa.column("effective_to", sa.DateTime(timezone=True)),
    sa.column("latest_request_id", sa.String(length=36)),
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
                attribute_entity.c.requester_id,
                attribute_entity.c.approver_id,
                attribute_entity.c.requester_ts,
                attribute_entity.c.approver_ts,
                attribute_entity.c.dictionary_action,
                attribute_entity.c.approval_status,
                attribute_entity.c.effective_from,
                attribute_entity.c.effective_to,
                attribute_entity.c.latest_request_id,
            )
            .where(attribute_entity.c.id == attribute_id)
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()

    async def get_by_id_for_update(self, session: AsyncSession, attribute_id: str):
        statement = (
            sa.select(attribute_entity)
            .where(attribute_entity.c.id == attribute_id)
            .with_for_update()
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
                attribute_entity.c.requester_id,
                attribute_entity.c.approver_id,
                attribute_entity.c.requester_ts,
                attribute_entity.c.approver_ts,
                attribute_entity.c.dictionary_action,
                attribute_entity.c.approval_status,
                attribute_entity.c.effective_from,
                attribute_entity.c.effective_to,
                attribute_entity.c.latest_request_id,
            )
            .where(attribute_entity.c.table_id == table_id)
            .where(sa.func.coalesce(attribute_entity.c.record_status, "A") == "A")
        )
        result = await session.execute(statement)
        return result.mappings().all()

    async def insert_current(
        self,
        session: AsyncSession,
        metadata_json: Dict[str, Any],
        requester_id: str,
        approver_id: str,
        requester_ts,
        approver_ts,
        version_seq: int,
        request_id: str,
    ) -> None:
        statement = sa.insert(attribute_entity).values(
            {
                "metadata": metadata_json,
                "requester_id": requester_id,
                "approver_id": approver_id,
                "requester_ts": requester_ts,
                "approver_ts": approver_ts,
                "version_seq": version_seq,
                "dictionary_action": "A",
                "approval_status": "A",
                "record_status": "A",
                "effective_from": approver_ts,
                "effective_to": None,
                "latest_request_id": request_id,
            }
        )
        await session.execute(statement)

    async def update_current(
        self,
        session: AsyncSession,
        attribute_id: str,
        metadata_json: Dict[str, Any],
        requester_id: str,
        approver_id: str,
        requester_ts,
        approver_ts,
        version_seq: int,
        request_id: str,
    ) -> None:
        statement = (
            sa.update(attribute_entity)
            .where(attribute_entity.c.id == attribute_id)
            .values(
                metadata=metadata_json,
                requester_id=requester_id,
                approver_id=approver_id,
                requester_ts=requester_ts,
                approver_ts=approver_ts,
                version_seq=version_seq,
                dictionary_action="U",
                approval_status="A",
                record_status="A",
                effective_from=approver_ts,
                effective_to=None,
                latest_request_id=request_id,
            )
        )
        await session.execute(statement)

    async def soft_delete_current(
        self,
        session: AsyncSession,
        attribute_id: str,
        metadata_json: Dict[str, Any],
        requester_id: str,
        approver_id: str,
        requester_ts,
        approver_ts,
        version_seq: int,
        request_id: str,
    ) -> None:
        statement = (
            sa.update(attribute_entity)
            .where(attribute_entity.c.id == attribute_id)
            .values(
                metadata=metadata_json,
                requester_id=requester_id,
                approver_id=approver_id,
                requester_ts=requester_ts,
                approver_ts=approver_ts,
                version_seq=version_seq,
                dictionary_action="D",
                approval_status="A",
                record_status="D",
                effective_to=approver_ts,
                latest_request_id=request_id,
            )
        )
        await session.execute(statement)

    async def insert_history(
        self,
        session: AsyncSession,
        history_id: str,
        current_row,
        requester_id: Optional[str],
        approver_id: str,
        requester_ts,
        approver_ts,
        dictionary_action: str,
        source_request_id: str,
    ) -> None:
        statement = sa.insert(AttributeEntityHistory.__table__).values(
            {
                "history_id": history_id,
                "attribute_id": current_row["id"],
                "metadata": current_row["metadata"],
                "version_seq": current_row["version_seq"],
                "requester_id": requester_id,
                "approver_id": approver_id,
                "requester_ts": requester_ts,
                "approver_ts": approver_ts,
                "dictionary_action": dictionary_action,
                "approval_status": "A",
                "record_status": current_row["record_status"] or "A",
                "effective_from": current_row["effective_from"],
                "effective_to": approver_ts,
                "source_request_id": source_request_id,
                "archived_at": approver_ts,
            }
        )
        await session.execute(statement)
