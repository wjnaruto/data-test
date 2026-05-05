from __future__ import annotations

from typing import Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.maker_checker import ApprovalRequest


class ApprovalRequestRepository:

    async def create_pending_request(
        self,
        session: AsyncSession,
        request_id: str,
        source_type: str,
        domain_id: str,
        tenant_unique_id: str,
        submitted_by: str,
        submitted_by_name: str,
        maker_comment: Optional[str],
        total_items: int,
    ) -> ApprovalRequest:
        request_row = ApprovalRequest(
            request_id=request_id,
            source_type=source_type,
            domain_id=domain_id,
            tenant_unique_id=tenant_unique_id,
            submitted_by=submitted_by,
            submitted_by_name=submitted_by_name,
            maker_comment=maker_comment,
            request_status="PENDING",
            total_items=total_items,
            approved_items=0,
            rejected_items=0,
        )
        session.add(request_row)
        await session.flush()
        return request_row

    async def get_by_id_for_update(self, session: AsyncSession, request_id: str):
        statement = (
            sa.select(ApprovalRequest.__table__)
            .where(ApprovalRequest.__table__.c.request_id == request_id)
            .with_for_update()
            .limit(1)
        )
        result = await session.execute(statement)
        return result.mappings().first()

    async def update_review_summary(
        self,
        session: AsyncSession,
        request_id: str,
        request_status: str,
        approved_items: int,
        rejected_items: int,
        reviewed_by: str,
        reviewed_by_name: Optional[str],
        reviewed_at,
        checker_comment: Optional[str],
    ) -> None:
        statement = (
            sa.update(ApprovalRequest.__table__)
            .where(ApprovalRequest.__table__.c.request_id == request_id)
            .values(
                request_status=request_status,
                approved_items=approved_items,
                rejected_items=rejected_items,
                reviewed_by=reviewed_by,
                reviewed_by_name=reviewed_by_name,
                reviewed_at=reviewed_at,
                checker_comment=checker_comment,
                updated_at=reviewed_at,
            )
        )
        await session.execute(statement)
