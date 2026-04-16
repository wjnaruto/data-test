from __future__ import annotations

import json
from typing import Any, Dict, Optional


async def get_current_dataset_by_id(connection, table_id: str):
    query = """
        SELECT id, table_metadata, version_seq, domain_id, tenant_unique_id, record_status
        FROM table_entity
        WHERE id = $1
    """
    return await connection.fetchrow(query, table_id)


async def get_current_attribute_by_id(connection, attribute_id: str):
    query = """
        SELECT id, metadata, version_seq, domain_id, tenant_unique_id, table_id, record_status
        FROM attribute_entity
        WHERE id = $1
    """
    return await connection.fetchrow(query, attribute_id)


async def get_active_attributes_by_table_id(connection, table_id: str):
    query = """
        SELECT id, metadata, version_seq, domain_id, tenant_unique_id, table_id, record_status
        FROM attribute_entity
        WHERE table_id = $1
          AND COALESCE(record_status, 'A') = 'A'
    """
    return await connection.fetch(query, table_id)


async def find_pending_dataset_conflict_by_target_id(connection, target_table_id: str):
    query = """
        SELECT p.pending_id, p.request_id
        FROM table_entity_pending p
        WHERE p.target_table_id = $1
          AND p.approval_status = 'P'
        LIMIT 1
    """
    return await connection.fetchrow(query, target_table_id)


async def find_pending_dataset_conflict_by_business_key(connection, domain_id: str, tenant_unique_id: str, table_name: str):
    query = """
        SELECT p.pending_id, p.request_id
        FROM table_entity_pending p
        WHERE p.approval_status = 'P'
          AND p.domain_id = $1
          AND p.tenant_unique_id = $2
          AND LOWER(p.table_name) = LOWER($3)
        LIMIT 1
    """
    return await connection.fetchrow(query, domain_id, tenant_unique_id, table_name)


async def find_pending_attribute_conflict_by_target_id(connection, target_attribute_id: str):
    query = """
        SELECT p.pending_id, p.request_id
        FROM attribute_entity_pending p
        WHERE p.target_attribute_id = $1
          AND p.approval_status = 'P'
        LIMIT 1
    """
    return await connection.fetchrow(query, target_attribute_id)


async def find_pending_attribute_conflict_by_business_key(
    connection,
    table_id: str,
    tenant_unique_id: str,
    field_name: str,
):
    query = """
        SELECT p.pending_id, p.request_id
        FROM attribute_entity_pending p
        WHERE p.approval_status = 'P'
          AND p.table_id = $1
          AND p.tenant_unique_id = $2
          AND LOWER(p.field_name) = LOWER($3)
        LIMIT 1
    """
    return await connection.fetchrow(query, table_id, tenant_unique_id, field_name)


async def insert_approval_request(
    connection,
    request_id: str,
    source_type: str,
    domain_id: str,
    tenant_unique_id: str,
    submitted_by: str,
    submitted_by_name: str,
    maker_comment: Optional[str],
    total_items: int,
) -> None:
    query = """
        INSERT INTO approval_request (
            request_id,
            source_type,
            domain_id,
            tenant_unique_id,
            submitted_by,
            submitted_by_name,
            maker_comment,
            request_status,
            total_items,
            approved_items,
            rejected_items
        )
        VALUES (
            $1, $2, $3, $4, $5, $6, $7, 'PENDING', $8, 0, 0
        )
    """
    await connection.execute(
        query,
        request_id,
        source_type,
        domain_id,
        tenant_unique_id,
        submitted_by,
        submitted_by_name,
        maker_comment,
        total_items,
    )


async def insert_table_pending(
    connection,
    pending_id: str,
    request_id: str,
    target_table_id: Optional[str],
    table_metadata: Dict[str, Any],
    dictionary_action: str,
    current_version_seq: Optional[int],
    target_version_seq: Optional[int],
    requester_id: str,
    maker_comment: Optional[str],
    current_snapshot: Optional[Dict[str, Any]],
) -> None:
    query = """
        INSERT INTO table_entity_pending (
            pending_id,
            request_id,
            target_table_id,
            table_metadata,
            dictionary_action,
            approval_status,
            current_version_seq,
            target_version_seq,
            requester_id,
            maker_comment,
            current_snapshot
        )
        VALUES (
            $1,
            $2,
            $3,
            $4::jsonb,
            $5,
            'P',
            $6,
            $7,
            $8,
            $9,
            $10::jsonb
        )
    """
    await connection.execute(
        query,
        pending_id,
        request_id,
        target_table_id,
        json.dumps(table_metadata),
        dictionary_action,
        current_version_seq,
        target_version_seq,
        requester_id,
        maker_comment,
        json.dumps(current_snapshot) if current_snapshot is not None else None,
    )


async def insert_attribute_pending(
    connection,
    pending_id: str,
    request_id: str,
    target_attribute_id: Optional[str],
    metadata: Dict[str, Any],
    dictionary_action: str,
    current_version_seq: Optional[int],
    target_version_seq: Optional[int],
    requester_id: str,
    maker_comment: Optional[str],
    current_snapshot: Optional[Dict[str, Any]],
) -> None:
    query = """
        INSERT INTO attribute_entity_pending (
            pending_id,
            request_id,
            target_attribute_id,
            metadata,
            dictionary_action,
            approval_status,
            current_version_seq,
            target_version_seq,
            requester_id,
            maker_comment,
            current_snapshot
        )
        VALUES (
            $1,
            $2,
            $3,
            $4::jsonb,
            $5,
            'P',
            $6,
            $7,
            $8,
            $9,
            $10::jsonb
        )
    """
    await connection.execute(
        query,
        pending_id,
        request_id,
        target_attribute_id,
        json.dumps(metadata),
        dictionary_action,
        current_version_seq,
        target_version_seq,
        requester_id,
        maker_comment,
        json.dumps(current_snapshot) if current_snapshot is not None else None,
    )
