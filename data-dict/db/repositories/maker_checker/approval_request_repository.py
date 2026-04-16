from __future__ import annotations

from typing import Optional

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
