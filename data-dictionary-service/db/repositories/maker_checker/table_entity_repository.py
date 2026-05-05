from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.maker_checker import TableEntityHistory


table_entity = sa.table(
    "table_entity",
    sa.column("id", sa.String(length=36)),
    sa.column("table_metadata", JSONB),
    sa.column("version_seq", sa.Integer()),
    sa.column("domain_id", sa.String(length=36)),
    sa.column("tenant_unique_id", sa.String(length=36)),
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
                table_entity.c.requester_id,
                table_entity.c.approver_id,
                table_entity.c.requester_ts,
                table_entity.c.approver_ts,
                table_entity.c.dictionary_action,
                table_entity.c.approval_status,
                table_entity.c.effective_from,
                table_entity.c.effective_to,
                table_entity.c.latest_request_id,
            )
            .where(table_entity.c.id == table_id)
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()

    async def get_by_id_for_update(self, session: AsyncSession, table_id: str):
        statement = (
            sa.select(table_entity)
            .where(table_entity.c.id == table_id)
            .with_for_update()
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()

    async def insert_current(
        self,
        session: AsyncSession,
        table_metadata: Dict[str, Any],
        requester_id: str,
        approver_id: str,
        requester_ts,
        approver_ts,
        version_seq: int,
        request_id: str,
    ) -> None:
        statement = sa.insert(table_entity).values(
            {
                "table_metadata": table_metadata,
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
        table_id: str,
        table_metadata: Dict[str, Any],
        requester_id: str,
        approver_id: str,
        requester_ts,
        approver_ts,
        version_seq: int,
        request_id: str,
    ) -> None:
        statement = (
            sa.update(table_entity)
            .where(table_entity.c.id == table_id)
            .values(
                table_metadata=table_metadata,
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
        table_id: str,
        table_metadata: Dict[str, Any],
        requester_id: str,
        approver_id: str,
        requester_ts,
        approver_ts,
        version_seq: int,
        request_id: str,
    ) -> None:
        statement = (
            sa.update(table_entity)
            .where(table_entity.c.id == table_id)
            .values(
                table_metadata=table_metadata,
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
        statement = sa.insert(TableEntityHistory.__table__).values(
            {
                "history_id": history_id,
                "table_id": current_row["id"],
                "table_metadata": current_row["table_metadata"],
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
