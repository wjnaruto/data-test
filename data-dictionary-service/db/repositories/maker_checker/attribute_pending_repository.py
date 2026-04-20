from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.maker_checker import AttributeEntityPending


class AttributePendingRepository:

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
    ) -> AttributeEntityPending:
        row = AttributeEntityPending(
            pending_id=pending_id,
            request_id=request_id,
            target_attribute_id=target_attribute_id,
            metadata_json=metadata_json,
            dictionary_action=dictionary_action,
            approval_status="P",
            current_version_seq=current_version_seq,
            target_version_seq=target_version_seq,
            requester_id=requester_id,
            maker_comment=maker_comment,
            current_snapshot=current_snapshot,
        )
        session.add(row)
        await session.flush()
        return row
