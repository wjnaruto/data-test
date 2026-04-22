from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from core.config import get_logger
from db.session import db
from schemas.maker_checker.submit import (
    AttributeSubmitItem,
    DatasetSubmitItem,
    SubmitConflictItem,
    SubmitRequest,
    SubmitResponse,
)
from db.repositories.maker_checker import (
    ApprovalRequestRepository,
    AttributeEntityRepository,
    AttributePendingRepository,
    TableEntityRepository,
    TablePendingRepository,
)
from services.access_control import UserAccessContext
from services.maker_checker.metadata_transformer import (
    attribute_input_to_metadata,
    dataset_input_to_table_metadata,
)


logger = get_logger(__name__)


@dataclass
class ResolvedDatasetItem:
    item: DatasetSubmitItem
    proposed_table_id: str


class SubmitService:

    def __init__(self):
        self.approval_request_repository = ApprovalRequestRepository()
        self.table_entity_repository = TableEntityRepository()
        self.attribute_entity_repository = AttributeEntityRepository()
        self.table_pending_repository = TablePendingRepository()
        self.attribute_pending_repository = AttributePendingRepository()

    async def submit(self, payload: SubmitRequest, user: UserAccessContext) -> SubmitResponse:
        if db.engine is None:
            raise HTTPException(status_code=500, detail="Database engine is not initialized.")

        user.require_requester(payload.tenantUniqueId)

        async with db.session() as session:
            async with session.begin():
                resolved_datasets, dataset_ids_by_client_ref = self._resolve_dataset_items(payload.datasets)
                dataset_conflicts = await self._collect_dataset_conflicts(session, payload, resolved_datasets)
                attribute_conflicts = await self._collect_attribute_conflicts(
                    session,
                    payload,
                    dataset_ids_by_client_ref,
                )
                conflicts = dataset_conflicts + attribute_conflicts

                if conflicts:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "PENDING_CONFLICT",
                            "message": "Submit failed because at least one item already has a pending request.",
                            "conflicts": [conflict.model_dump() for conflict in conflicts],
                        },
                    )

                request_id = str(uuid4())
                attribute_items = self._expand_attribute_items(payload)

                total_items = len(resolved_datasets) + len(attribute_items)
                await self.approval_request_repository.create_pending_request(
                    session=session,
                    request_id=request_id,
                    source_type=payload.sourceType,
                    domain_id=payload.domainId,
                    tenant_unique_id=payload.tenantUniqueId,
                    submitted_by=user.user_id,
                    submitted_by_name=user.user_name,
                    maker_comment=payload.makerComment,
                    total_items=total_items,
                )

                for resolved_dataset in resolved_datasets:
                    await self._stage_dataset(
                        session=session,
                        request_id=request_id,
                        payload=payload,
                        dataset_item=resolved_dataset.item,
                        proposed_table_id=resolved_dataset.proposed_table_id,
                        user=user,
                    )

                for attribute_item in attribute_items:
                    await self._stage_attribute(
                        session=session,
                        request_id=request_id,
                        payload=payload,
                        attribute_item=attribute_item,
                        dataset_ids_by_client_ref=dataset_ids_by_client_ref,
                        user=user,
                    )

                return SubmitResponse(
                    requestId=request_id,
                    requestStatus="PENDING",
                    totalItems=total_items,
                    datasetItems=len(resolved_datasets),
                    attributeItems=len(attribute_items),
                    message="Submit accepted and staged in pending tables.",
                )

    def _resolve_dataset_items(self, dataset_items: List[DatasetSubmitItem]) -> tuple[List[ResolvedDatasetItem], Dict[str, str]]:
        resolved_items: List[ResolvedDatasetItem] = []
        dataset_ids_by_client_ref: Dict[str, str] = {}

        for dataset_item in dataset_items:
            proposed_table_id = str(uuid4()) if dataset_item.action == "A" else dataset_item.entityId
            if not proposed_table_id:
                raise HTTPException(status_code=400, detail="Dataset entityId is required for update/delete.")

            if dataset_item.clientRef:
                if dataset_item.clientRef in dataset_ids_by_client_ref:
                    raise HTTPException(status_code=400, detail=f"Duplicate dataset clientRef: {dataset_item.clientRef}")
                dataset_ids_by_client_ref[dataset_item.clientRef] = proposed_table_id

            resolved_items.append(ResolvedDatasetItem(item=dataset_item, proposed_table_id=proposed_table_id))

        return resolved_items, dataset_ids_by_client_ref

    async def _collect_dataset_conflicts(
        self,
        session,
        payload: SubmitRequest,
        resolved_datasets: List[ResolvedDatasetItem],
    ) -> List[SubmitConflictItem]:
        conflicts: List[SubmitConflictItem] = []

        for resolved_dataset in resolved_datasets:
            dataset_item = resolved_dataset.item
            proposed_table_id = resolved_dataset.proposed_table_id

            if dataset_item.action in {"U", "D"} and dataset_item.entityId:
                current_dataset = await self.table_entity_repository.get_by_id(session, dataset_item.entityId)
                if current_dataset is None:
                    raise HTTPException(status_code=404, detail=f"Dataset {dataset_item.entityId} not found.")
                if current_dataset["tenant_unique_id"] != payload.tenantUniqueId:
                    raise HTTPException(status_code=403, detail="Dataset tenant does not match submit tenant.")

                pending_conflict = await self.table_pending_repository.find_pending_conflict_by_target_id(
                    session, dataset_item.entityId
                )
                if pending_conflict:
                    conflicts.append(
                        SubmitConflictItem(
                            entityType="DATASET",
                            action=dataset_item.action,
                            entityId=dataset_item.entityId,
                            businessKey=f"dataset:{dataset_item.entityId}",
                            existingRequestId=pending_conflict["request_id"],
                            message="A pending dataset request already exists for this dataset.",
                        )
                    )
                continue

            if dataset_item.action == "A":
                table_name = dataset_item.tableMetadata.tableName
                if not table_name:
                    raise HTTPException(status_code=400, detail="Dataset add requires tableName in tableMetadata.")
                pending_conflict = await self.table_pending_repository.find_pending_conflict_by_business_key(
                    session,
                    payload.domainId,
                    payload.tenantUniqueId,
                    table_name,
                )
                if pending_conflict:
                    conflicts.append(
                        SubmitConflictItem(
                            entityType="DATASET",
                            action="A",
                            entityId=proposed_table_id,
                            businessKey=f"dataset:{payload.domainId}:{payload.tenantUniqueId}:{table_name.lower()}",
                            existingRequestId=pending_conflict["request_id"],
                            message="A pending dataset request already exists for the same dataset business key.",
                        )
                    )

        return conflicts

    async def _collect_attribute_conflicts(
        self,
        session,
        payload: SubmitRequest,
        dataset_ids_by_client_ref: Dict[str, str],
    ) -> List[SubmitConflictItem]:
        conflicts: List[SubmitConflictItem] = []

        for attribute_item in payload.attributes:
            if attribute_item.action in {"U", "D"} and attribute_item.entityId:
                current_attribute = await self.attribute_entity_repository.get_by_id(session, attribute_item.entityId)
                if current_attribute is None:
                    raise HTTPException(status_code=404, detail=f"Attribute {attribute_item.entityId} not found.")
                if current_attribute["tenant_unique_id"] != payload.tenantUniqueId:
                    raise HTTPException(status_code=403, detail="Attribute tenant does not match submit tenant.")

                pending_conflict = await self.attribute_pending_repository.find_pending_conflict_by_target_id(
                    session, attribute_item.entityId
                )
                if pending_conflict:
                    conflicts.append(
                        SubmitConflictItem(
                            entityType="ATTRIBUTE",
                            action=attribute_item.action,
                            entityId=attribute_item.entityId,
                            businessKey=f"attribute:{attribute_item.entityId}",
                            existingRequestId=pending_conflict["request_id"],
                            message="A pending attribute request already exists for this attribute.",
                        )
                    )
                continue

            if attribute_item.action == "A":
                table_id = await self._resolve_attribute_table_id(
                    session,
                    attribute_item,
                    dataset_ids_by_client_ref,
                    payload.tenantUniqueId,
                )
                field_name = attribute_item.metadata.fieldName
                if not table_id:
                    raise HTTPException(status_code=400, detail="Attribute add requires tableId or datasetClientRef.")
                if not field_name:
                    raise HTTPException(status_code=400, detail="Attribute add requires Field Name in metadata.")

                pending_conflict = await self.attribute_pending_repository.find_pending_conflict_by_business_key(
                    session,
                    table_id,
                    payload.tenantUniqueId,
                    field_name,
                )
                if pending_conflict:
                    conflicts.append(
                        SubmitConflictItem(
                            entityType="ATTRIBUTE",
                            action="A",
                            entityId=None,
                            businessKey=f"attribute:{table_id}:{payload.tenantUniqueId}:{field_name.lower()}",
                            existingRequestId=pending_conflict["request_id"],
                            message="A pending attribute request already exists for the same attribute business key.",
                        )
                    )

        return conflicts

    def _expand_attribute_items(self, payload: SubmitRequest) -> List[AttributeSubmitItem]:
        return list(payload.attributes)

    async def _stage_dataset(
        self,
        session,
        request_id: str,
        payload: SubmitRequest,
        dataset_item: DatasetSubmitItem,
        proposed_table_id: Optional[str],
        user: UserAccessContext,
    ) -> None:
        current_snapshot = None
        current_version_seq = None
        target_version_seq = None

        if dataset_item.action == "A":
            target_version_seq = 1
        else:
            current_dataset = await self.table_entity_repository.get_by_id(session, dataset_item.entityId)
            if current_dataset is None:
                raise HTTPException(status_code=404, detail=f"Dataset {dataset_item.entityId} not found.")
            current_snapshot = self._coerce_json(current_dataset["table_metadata"])
            current_version_seq = current_dataset["version_seq"]
            target_version_seq = (current_version_seq or 0) + 1 if dataset_item.action == "U" else current_version_seq

        normalized_metadata = self._normalize_dataset_metadata(
            metadata=dataset_item.tableMetadata,
            base_metadata=current_snapshot,
            proposed_table_id=proposed_table_id,
            payload=payload,
            user=user,
            is_add=dataset_item.action == "A",
            is_delete=dataset_item.action == "D",
        )

        pending_target_table_id = None if dataset_item.action == "A" else proposed_table_id
        logger.info(
            "Staging dataset pending item: action=%s, proposed_table_id=%s, pending_target_table_id=%s",
            dataset_item.action,
            proposed_table_id,
            pending_target_table_id,
        )

        await self.table_pending_repository.create_pending(
            session=session,
            pending_id=str(uuid4()),
            request_id=request_id,
            target_table_id=pending_target_table_id,
            table_metadata=normalized_metadata,
            dictionary_action=dataset_item.action,
            current_version_seq=current_version_seq,
            target_version_seq=target_version_seq,
            requester_id=user.user_id,
            maker_comment=payload.makerComment,
            current_snapshot=current_snapshot,
        )

    async def _stage_attribute(
        self,
        session,
        request_id: str,
        payload: SubmitRequest,
        attribute_item: AttributeSubmitItem,
        dataset_ids_by_client_ref: Dict[str, str],
        user: UserAccessContext,
    ) -> None:
        current_snapshot = None
        current_version_seq = None
        target_version_seq = None
        target_attribute_id = attribute_item.entityId
        current_table_id = None

        if attribute_item.action == "A":
            target_attribute_id = str(uuid4())
            target_version_seq = 1
        else:
            current_attribute = await self.attribute_entity_repository.get_by_id(session, attribute_item.entityId)
            if current_attribute is None:
                raise HTTPException(status_code=404, detail=f"Attribute {attribute_item.entityId} not found.")
            current_snapshot = self._coerce_json(current_attribute["metadata"])
            current_version_seq = current_attribute["version_seq"]
            current_table_id = current_attribute["table_id"]
            target_version_seq = (current_version_seq or 0) + 1 if attribute_item.action == "U" else current_version_seq

        resolved_table_id = await self._resolve_attribute_table_id(
            session,
            attribute_item,
            dataset_ids_by_client_ref,
            payload.tenantUniqueId,
            require_for_add=attribute_item.action == "A",
        )
        if resolved_table_id is None:
            resolved_table_id = current_table_id

        normalized_metadata = self._normalize_attribute_metadata(
            metadata=attribute_item.metadata,
            base_metadata=current_snapshot,
            attribute_id=target_attribute_id,
            dataset_id=resolved_table_id,
            payload=payload,
            user=user,
            is_add=attribute_item.action == "A",
            is_delete=attribute_item.action == "D",
        )

        await self.attribute_pending_repository.create_pending(
            session=session,
            pending_id=str(uuid4()),
            request_id=request_id,
            target_attribute_id=None if attribute_item.action == "A" else target_attribute_id,
            metadata_json=normalized_metadata,
            dictionary_action=attribute_item.action,
            current_version_seq=current_version_seq,
            target_version_seq=target_version_seq,
            requester_id=user.user_id,
            maker_comment=payload.makerComment,
            current_snapshot=current_snapshot,
        )

    def _normalize_dataset_metadata(
        self,
        metadata,
        base_metadata: Optional[Dict[str, Any]],
        proposed_table_id: Optional[str],
        payload: SubmitRequest,
        user: UserAccessContext,
        is_add: bool,
        is_delete: bool,
    ) -> Dict[str, Any]:
        normalized = dict(base_metadata or {})
        normalized.update(dataset_input_to_table_metadata(metadata))
        timestamp = self._current_epoch_millis()
        if proposed_table_id:
            normalized["id"] = proposed_table_id
        self._validate_scope(normalized.get("domainId"), payload.domainId, "dataset domainId")
        self._validate_scope(normalized.get("tenantUniqueId"), payload.tenantUniqueId, "dataset tenantUniqueId")
        normalized["domainId"] = payload.domainId
        normalized["tenantUniqueId"] = payload.tenantUniqueId
        normalized["updatedAt"] = timestamp
        normalized["updatedBy"] = user.user_id
        if is_add and "createdAt" not in normalized:
            normalized["createdAt"] = timestamp
        normalized["deleted"] = is_delete
        return normalized

    def _normalize_attribute_metadata(
        self,
        metadata,
        base_metadata: Optional[Dict[str, Any]],
        attribute_id: Optional[str],
        dataset_id: Optional[str],
        payload: SubmitRequest,
        user: UserAccessContext,
        is_add: bool,
        is_delete: bool,
    ) -> Dict[str, Any]:
        normalized = dict(base_metadata or {})
        normalized.update(attribute_input_to_metadata(metadata))
        timestamp = self._current_epoch_millis()
        if attribute_id:
            normalized["id"] = attribute_id
        if dataset_id and not normalized.get("tableId"):
            normalized["tableId"] = dataset_id

        self._validate_scope(normalized.get("domainId"), payload.domainId, "attribute domainId")
        self._validate_scope(normalized.get("tenantUniqueId"), payload.tenantUniqueId, "attribute tenantUniqueId")
        if not normalized.get("tableId"):
            raise HTTPException(status_code=400, detail="Attribute metadata must include tableId.")

        normalized["domainId"] = payload.domainId
        normalized["tenantUniqueId"] = payload.tenantUniqueId
        normalized["updatedAt"] = timestamp
        normalized["updatedBy"] = user.user_id
        if is_add and "createdAt" not in normalized:
            normalized["createdAt"] = timestamp
        normalized["deleted"] = is_delete
        return normalized

    async def _resolve_attribute_table_id(
        self,
        session,
        attribute_item: AttributeSubmitItem,
        dataset_ids_by_client_ref: Dict[str, str],
        tenant_unique_id: str,
        require_for_add: bool = False,
    ) -> Optional[str]:
        metadata_table_id = attribute_item.metadata.tableId

        if attribute_item.datasetClientRef:
            resolved_table_id = dataset_ids_by_client_ref.get(attribute_item.datasetClientRef)
            if not resolved_table_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"datasetClientRef {attribute_item.datasetClientRef} does not match any dataset add in this submit.",
                )
            if metadata_table_id and metadata_table_id != resolved_table_id:
                raise HTTPException(
                    status_code=400,
                    detail="Attribute tableId does not match the resolved datasetClientRef.",
                )
            return resolved_table_id

        if metadata_table_id:
            dataset = await self.table_entity_repository.get_by_id(session, metadata_table_id)
            if dataset is None:
                raise HTTPException(status_code=404, detail=f"Dataset {metadata_table_id} not found for attribute.")
            if dataset["tenant_unique_id"] != tenant_unique_id:
                raise HTTPException(status_code=403, detail="Attribute dataset tenant does not match submit tenant.")
            return metadata_table_id

        if require_for_add:
            raise HTTPException(status_code=400, detail="Attribute add requires tableId or datasetClientRef.")

        return None

    def _validate_scope(self, incoming_value: Optional[str], expected_value: str, field_name: str) -> None:
        if incoming_value and incoming_value != expected_value:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} does not match submit scope.",
            )

    def _coerce_json(self, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return json.loads(value)
        return dict(value)

    def _current_epoch_millis(self) -> int:
        from datetime import datetime

        return int(datetime.utcnow().timestamp() * 1000)
