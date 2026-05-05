from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set
from uuid import uuid4

from fastapi import HTTPException

from core.config import get_logger
from db.repositories.maker_checker import (
    ApprovalRequestRepository,
    AttributeEntityRepository,
    AttributePendingRepository,
    TableEntityRepository,
    TablePendingRepository,
)
from db.session import db
from schemas.maker_checker.review import (
    FailedReviewItem,
    ProcessedRequest,
    ProcessedReviewItem,
    ReviewRequest,
    ReviewResponse,
)
from services.access_control import UserAccessContext


logger = get_logger(__name__)


@dataclass
class ReviewGroup:
    table_pending_ids: Set[str] = field(default_factory=set)
    attribute_pending_ids: Set[str] = field(default_factory=set)
    scopes: Set[str] = field(default_factory=set)


class ReviewService:

    def __init__(self):
        self.approval_request_repository = ApprovalRequestRepository()
        self.table_pending_repository = TablePendingRepository()
        self.attribute_pending_repository = AttributePendingRepository()
        self.table_entity_repository = TableEntityRepository()
        self.attribute_entity_repository = AttributeEntityRepository()

    async def approve(self, payload: ReviewRequest, user: UserAccessContext) -> ReviewResponse:
        return await self._review(payload=payload, user=user, action="APPROVE")

    async def reject(self, payload: ReviewRequest, user: UserAccessContext) -> ReviewResponse:
        return await self._review(payload=payload, user=user, action="REJECT")

    async def _review(self, payload: ReviewRequest, user: UserAccessContext, action: str) -> ReviewResponse:
        if db.engine is None:
            raise HTTPException(status_code=500, detail="Database engine is not initialized.")

        groups = await self._build_review_groups(payload)
        processed_requests: List[ProcessedRequest] = []

        for request_id, group in groups.items():
            async with db.session() as session:
                async with session.begin():
                    processed_requests.append(
                        await self._process_request_group(
                            session=session,
                            request_id=request_id,
                            group=group,
                            action=action,
                            user=user,
                            checker_comment=payload.checkerComment,
                        )
                    )

        return ReviewResponse(processedRequests=processed_requests, failedItems=[])

    async def _build_review_groups(self, payload: ReviewRequest) -> Dict[str, ReviewGroup]:
        groups: Dict[str, ReviewGroup] = defaultdict(ReviewGroup)
        table_ids = [item.pendingId for item in payload.items if item.itemType == "DATASET"]
        attribute_ids = [item.pendingId for item in payload.items if item.itemType == "ATTRIBUTE"]

        async with db.session() as session:
            table_rows = await self.table_pending_repository.get_by_ids_for_update(session, table_ids)
            attribute_rows = await self.attribute_pending_repository.get_by_ids_for_update(session, attribute_ids)

        found_table_ids = {row["pending_id"] for row in table_rows}
        missing_table_ids = set(table_ids) - found_table_ids
        if missing_table_ids:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "PENDING_ITEM_NOT_FOUND",
                    "message": "Dataset pending item was not found.",
                    "details": {"pendingIds": sorted(missing_table_ids)},
                },
            )

        found_attribute_ids = {row["pending_id"] for row in attribute_rows}
        missing_attribute_ids = set(attribute_ids) - found_attribute_ids
        if missing_attribute_ids:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "PENDING_ITEM_NOT_FOUND",
                    "message": "Attribute pending item was not found.",
                    "details": {"pendingIds": sorted(missing_attribute_ids)},
                },
            )

        for row in table_rows:
            groups[row["request_id"]].table_pending_ids.add(row["pending_id"])

        for row in attribute_rows:
            groups[row["request_id"]].attribute_pending_ids.add(row["pending_id"])

        for request_selection in payload.requests:
            groups[request_selection.requestId].scopes.add(request_selection.itemTypeScope)

        return dict(groups)

    async def _process_request_group(
        self,
        session,
        request_id: str,
        group: ReviewGroup,
        action: str,
        user: UserAccessContext,
        checker_comment: Optional[str],
    ) -> ProcessedRequest:
        request_row = await self.approval_request_repository.get_by_id_for_update(session, request_id)
        if request_row is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "REQUEST_NOT_FOUND", "message": f"Approval request {request_id} was not found."},
            )

        user.require_approver(request_row["tenant_unique_id"])
        if request_row["submitted_by"] == user.user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "SELF_REVIEW_NOT_ALLOWED",
                    "message": "A requester cannot approve or reject their own request.",
                },
            )

        table_rows = await self._load_selected_table_pending_rows(session, request_id, group)
        attribute_rows = await self._load_selected_attribute_pending_rows(session, request_id, group)

        if not table_rows and not attribute_rows:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "NO_PENDING_ITEMS_FOR_SELECTION",
                    "message": "The selected request has no pending items for the selected scope.",
                },
            )

        self._validate_pending_rows(request_id, table_rows, attribute_rows)

        now = datetime.now(timezone.utc)
        if action == "APPROVE":
            processed_items = await self._approve_items(
                session=session,
                table_rows=table_rows,
                attribute_rows=attribute_rows,
                user=user,
                approver_ts=now,
                checker_comment=checker_comment,
            )
        else:
            processed_items = await self._reject_items(
                session=session,
                table_rows=table_rows,
                attribute_rows=attribute_rows,
                user=user,
                approver_ts=now,
                checker_comment=checker_comment,
            )

        approved_items, rejected_items, pending_items, request_status = await self._recalculate_request_status(
            session=session,
            request_id=request_id,
            total_items=request_row["total_items"],
        )
        await self.approval_request_repository.update_review_summary(
            session=session,
            request_id=request_id,
            request_status=request_status,
            approved_items=approved_items,
            rejected_items=rejected_items,
            reviewed_by=user.user_id,
            reviewed_by_name=user.user_name,
            reviewed_at=now,
            checker_comment=checker_comment,
        )

        return ProcessedRequest(
            requestId=request_id,
            requestStatus=request_status,
            approvedItems=approved_items,
            rejectedItems=rejected_items,
            pendingItems=pending_items,
            processedItems=processed_items,
        )

    async def _load_selected_table_pending_rows(self, session, request_id: str, group: ReviewGroup):
        rows_by_id = {}
        if "DATASET" in group.scopes or "ALL" in group.scopes:
            for row in await self.table_pending_repository.get_pending_by_request_for_update(session, request_id):
                rows_by_id[row["pending_id"]] = row

        if group.table_pending_ids:
            for row in await self.table_pending_repository.get_by_ids_for_update(session, group.table_pending_ids):
                rows_by_id[row["pending_id"]] = row

        return list(rows_by_id.values())

    async def _load_selected_attribute_pending_rows(self, session, request_id: str, group: ReviewGroup):
        rows_by_id = {}
        if "ATTRIBUTE" in group.scopes or "ALL" in group.scopes:
            for row in await self.attribute_pending_repository.get_pending_by_request_for_update(session, request_id):
                rows_by_id[row["pending_id"]] = row

        if group.attribute_pending_ids:
            for row in await self.attribute_pending_repository.get_by_ids_for_update(session, group.attribute_pending_ids):
                rows_by_id[row["pending_id"]] = row

        return list(rows_by_id.values())

    def _validate_pending_rows(self, request_id: str, table_rows, attribute_rows) -> None:
        for row in [*table_rows, *attribute_rows]:
            if row["request_id"] != request_id:
                raise HTTPException(status_code=400, detail="Pending item request_id does not match selected request.")
            if row["approval_status"] != "P":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "PENDING_ITEM_ALREADY_REVIEWED",
                        "message": "Pending item has already been approved or rejected.",
                        "details": {"pendingId": row["pending_id"]},
                    },
                )

    async def _approve_items(
        self,
        session,
        table_rows,
        attribute_rows,
        user: UserAccessContext,
        approver_ts,
        checker_comment: Optional[str],
    ) -> List[ProcessedReviewItem]:
        processed_items: List[ProcessedReviewItem] = []
        selected_attribute_ids = {row["pending_id"] for row in attribute_rows}

        inserted_table_ids: Set[str] = set()
        for row in self._sort_table_rows(table_rows, "A"):
            table_id = await self._approve_table_add(session, row, user, approver_ts)
            inserted_table_ids.add(table_id)
            processed_items.append(ProcessedReviewItem(itemType="DATASET", pendingId=row["pending_id"], status="APPROVED"))

        for row in self._sort_table_rows(table_rows, "U"):
            await self._approve_table_update(session, row, user, approver_ts)
            processed_items.append(ProcessedReviewItem(itemType="DATASET", pendingId=row["pending_id"], status="APPROVED"))

        for row in self._sort_attribute_rows(attribute_rows, "A"):
            await self._approve_attribute_add(session, row, user, approver_ts, inserted_table_ids)
            processed_items.append(ProcessedReviewItem(itemType="ATTRIBUTE", pendingId=row["pending_id"], status="APPROVED"))

        for row in self._sort_attribute_rows(attribute_rows, "U"):
            await self._approve_attribute_update(session, row, user, approver_ts)
            processed_items.append(ProcessedReviewItem(itemType="ATTRIBUTE", pendingId=row["pending_id"], status="APPROVED"))

        for row in self._sort_attribute_rows(attribute_rows, "D"):
            await self._approve_attribute_delete(session, row, user, approver_ts)
            processed_items.append(ProcessedReviewItem(itemType="ATTRIBUTE", pendingId=row["pending_id"], status="APPROVED"))

        for row in self._sort_table_rows(table_rows, "D"):
            await self._approve_table_delete(session, row, user, approver_ts, selected_attribute_ids)
            processed_items.append(ProcessedReviewItem(itemType="DATASET", pendingId=row["pending_id"], status="APPROVED"))

        await self.table_pending_repository.mark_reviewed(
            session=session,
            pending_ids=[item.pendingId for item in processed_items if item.itemType == "DATASET"],
            approval_status="A",
            approver_id=user.user_id,
            approver_ts=approver_ts,
            checker_comment=checker_comment,
        )
        await self.attribute_pending_repository.mark_reviewed(
            session=session,
            pending_ids=[item.pendingId for item in processed_items if item.itemType == "ATTRIBUTE"],
            approval_status="A",
            approver_id=user.user_id,
            approver_ts=approver_ts,
            checker_comment=checker_comment,
        )
        return processed_items

    async def _reject_items(
        self,
        session,
        table_rows,
        attribute_rows,
        user: UserAccessContext,
        approver_ts,
        checker_comment: Optional[str],
    ) -> List[ProcessedReviewItem]:
        table_ids = [row["pending_id"] for row in table_rows]
        attribute_ids = [row["pending_id"] for row in attribute_rows]
        await self.table_pending_repository.mark_reviewed(session, table_ids, "R", user.user_id, approver_ts, checker_comment)
        await self.attribute_pending_repository.mark_reviewed(session, attribute_ids, "R", user.user_id, approver_ts, checker_comment)

        return [
            *[ProcessedReviewItem(itemType="DATASET", pendingId=pending_id, status="REJECTED") for pending_id in table_ids],
            *[ProcessedReviewItem(itemType="ATTRIBUTE", pendingId=pending_id, status="REJECTED") for pending_id in attribute_ids],
        ]

    async def _approve_table_add(self, session, row, user: UserAccessContext, approver_ts) -> str:
        metadata = self._with_publish_controls(self._coerce_json(row["table_metadata"]), user.user_id, approver_ts, deleted=False)
        table_id = metadata.get("id")
        if not table_id:
            raise HTTPException(status_code=409, detail={"code": "MISSING_PROPOSED_TABLE_ID", "message": "Dataset add pending row has no proposed table id."})

        await self.table_entity_repository.insert_current(
            session=session,
            table_metadata=metadata,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            version_seq=row["target_version_seq"] or 1,
            request_id=row["request_id"],
        )
        return table_id

    async def _approve_table_update(self, session, row, user: UserAccessContext, approver_ts) -> None:
        current = await self._load_current_table_for_review(session, row)
        await self.table_entity_repository.insert_history(
            session=session,
            history_id=str(uuid4()),
            current_row=current,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            dictionary_action="U",
            source_request_id=row["request_id"],
        )
        merged = self._merge_metadata(current["table_metadata"], row["table_metadata"])
        merged = self._with_publish_controls(merged, user.user_id, approver_ts, deleted=False)
        await self.table_entity_repository.update_current(
            session=session,
            table_id=row["target_table_id"],
            table_metadata=merged,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            version_seq=row["target_version_seq"] or (current["version_seq"] or 0) + 1,
            request_id=row["request_id"],
        )

    async def _approve_table_delete(self, session, row, user: UserAccessContext, approver_ts, selected_attribute_ids: Set[str]) -> None:
        current = await self._load_current_table_for_review(session, row)
        unresolved_child_pending = await self.attribute_pending_repository.find_pending_by_table_ids(
            session,
            [row["target_table_id"]],
        )
        unresolved_child_pending = [
            pending_row for pending_row in unresolved_child_pending
            if pending_row["pending_id"] not in selected_attribute_ids
        ]
        if unresolved_child_pending:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "DATASET_DELETE_HAS_PENDING_ATTRIBUTES",
                    "message": "Dataset delete cannot be approved while child attribute pending items remain unresolved.",
                    "details": {"tableId": row["target_table_id"]},
                },
            )

        await self.table_entity_repository.insert_history(
            session=session,
            history_id=str(uuid4()),
            current_row=current,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            dictionary_action="D",
            source_request_id=row["request_id"],
        )

        active_attributes = await self.attribute_entity_repository.get_active_by_table_id(session, row["target_table_id"])
        for attribute in active_attributes:
            await self.attribute_entity_repository.insert_history(
                session=session,
                history_id=str(uuid4()),
                current_row=attribute,
                requester_id=row["requester_id"],
                approver_id=user.user_id,
                requester_ts=row["requester_ts"],
                approver_ts=approver_ts,
                dictionary_action="D",
                source_request_id=row["request_id"],
            )
            deleted_attribute_metadata = self._with_publish_controls(attribute["metadata"], user.user_id, approver_ts, deleted=True)
            await self.attribute_entity_repository.soft_delete_current(
                session=session,
                attribute_id=attribute["id"],
                metadata_json=deleted_attribute_metadata,
                requester_id=row["requester_id"],
                approver_id=user.user_id,
                requester_ts=row["requester_ts"],
                approver_ts=approver_ts,
                version_seq=attribute["version_seq"],
                request_id=row["request_id"],
            )

        deleted_table_metadata = self._with_publish_controls(current["table_metadata"], user.user_id, approver_ts, deleted=True)
        await self.table_entity_repository.soft_delete_current(
            session=session,
            table_id=row["target_table_id"],
            table_metadata=deleted_table_metadata,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            version_seq=current["version_seq"],
            request_id=row["request_id"],
        )

    async def _approve_attribute_add(self, session, row, user: UserAccessContext, approver_ts, inserted_table_ids: Set[str]) -> None:
        metadata = self._with_publish_controls(self._coerce_json(row["metadata"]), user.user_id, approver_ts, deleted=False)
        attribute_id = metadata.get("id")
        table_id = metadata.get("tableId")
        if not attribute_id:
            raise HTTPException(status_code=409, detail={"code": "MISSING_PROPOSED_ATTRIBUTE_ID", "message": "Attribute add pending row has no proposed attribute id."})
        if not table_id:
            raise HTTPException(status_code=409, detail={"code": "MISSING_PARENT_TABLE_ID", "message": "Attribute add pending row has no parent table id."})

        parent = await self.table_entity_repository.get_by_id_for_update(session, table_id)
        if parent is None and table_id not in inserted_table_ids:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "PARENT_DATASET_NOT_APPROVED",
                    "message": "Parent dataset has not been approved into the main table.",
                    "details": {"tableId": table_id},
                },
            )

        await self.attribute_entity_repository.insert_current(
            session=session,
            metadata_json=metadata,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            version_seq=row["target_version_seq"] or 1,
            request_id=row["request_id"],
        )

    async def _approve_attribute_update(self, session, row, user: UserAccessContext, approver_ts) -> None:
        current = await self._load_current_attribute_for_review(session, row)
        await self.attribute_entity_repository.insert_history(
            session=session,
            history_id=str(uuid4()),
            current_row=current,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            dictionary_action="U",
            source_request_id=row["request_id"],
        )
        merged = self._merge_metadata(current["metadata"], row["metadata"])
        merged = self._with_publish_controls(merged, user.user_id, approver_ts, deleted=False)
        await self.attribute_entity_repository.update_current(
            session=session,
            attribute_id=row["target_attribute_id"],
            metadata_json=merged,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            version_seq=row["target_version_seq"] or (current["version_seq"] or 0) + 1,
            request_id=row["request_id"],
        )

    async def _approve_attribute_delete(self, session, row, user: UserAccessContext, approver_ts) -> None:
        current = await self._load_current_attribute_for_review(session, row)
        await self.attribute_entity_repository.insert_history(
            session=session,
            history_id=str(uuid4()),
            current_row=current,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            dictionary_action="D",
            source_request_id=row["request_id"],
        )
        metadata = self._with_publish_controls(current["metadata"], user.user_id, approver_ts, deleted=True)
        await self.attribute_entity_repository.soft_delete_current(
            session=session,
            attribute_id=row["target_attribute_id"],
            metadata_json=metadata,
            requester_id=row["requester_id"],
            approver_id=user.user_id,
            requester_ts=row["requester_ts"],
            approver_ts=approver_ts,
            version_seq=current["version_seq"],
            request_id=row["request_id"],
        )

    async def _load_current_table_for_review(self, session, pending_row):
        current = await self.table_entity_repository.get_by_id_for_update(session, pending_row["target_table_id"])
        if current is None:
            raise HTTPException(status_code=404, detail={"code": "CURRENT_DATASET_NOT_FOUND", "message": "Current dataset was not found."})
        return current

    async def _load_current_attribute_for_review(self, session, pending_row):
        current = await self.attribute_entity_repository.get_by_id_for_update(session, pending_row["target_attribute_id"])
        if current is None:
            raise HTTPException(status_code=404, detail={"code": "CURRENT_ATTRIBUTE_NOT_FOUND", "message": "Current attribute was not found."})
        return current

    async def _recalculate_request_status(self, session, request_id: str, total_items: int):
        counts = {"P": 0, "A": 0, "R": 0}
        for row in await self.table_pending_repository.count_status_by_request(session, request_id):
            counts[row["approval_status"]] = row["item_count"]
        for row in await self.attribute_pending_repository.count_status_by_request(session, request_id):
            counts[row["approval_status"]] = counts.get(row["approval_status"], 0) + row["item_count"]

        approved_items = counts.get("A", 0)
        rejected_items = counts.get("R", 0)
        pending_items = counts.get("P", 0)

        if approved_items == total_items:
            status = "APPROVED"
        elif rejected_items == total_items:
            status = "REJECTED"
        elif pending_items == 0 and approved_items > 0 and rejected_items > 0:
            status = "COMPLETED_MIXED"
        elif pending_items > 0 and (approved_items > 0 or rejected_items > 0):
            status = "IN_REVIEW"
        else:
            status = "PENDING"

        return approved_items, rejected_items, pending_items, status

    def _sort_table_rows(self, rows, action: str):
        return [row for row in rows if row["dictionary_action"] == action]

    def _sort_attribute_rows(self, rows, action: str):
        return [row for row in rows if row["dictionary_action"] == action]

    def _merge_metadata(self, current_metadata: Any, pending_metadata: Any) -> Dict[str, Any]:
        merged = self._coerce_json(current_metadata)
        merged.update(self._coerce_json(pending_metadata))
        return merged

    def _with_publish_controls(self, metadata: Any, user_id: str, approver_ts, deleted: bool) -> Dict[str, Any]:
        result = self._coerce_json(metadata)
        result["deleted"] = deleted
        result["updatedAt"] = int(approver_ts.timestamp() * 1000)
        result["updatedBy"] = user_id
        if "createdAt" not in result:
            result["createdAt"] = int(approver_ts.timestamp() * 1000)
        return result

    def _coerce_json(self, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str):
            return json.loads(value)
        return dict(value)
