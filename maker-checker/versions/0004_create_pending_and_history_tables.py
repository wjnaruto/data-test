"""create pending and history tables

Revision ID: 0004_create_pending_and_history_tables
Revises: 0003_add_governance_columns_to_current_tables
Create Date: 2026-04-14
"""
from __future__ import annotations

from alembic import op


revision = "0004_create_pending_and_history_tables"
down_revision = "0003_add_governance_columns_to_current_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.table_entity_pending (
            pending_id varchar(36) NOT NULL,
            request_id varchar(36) NOT NULL,
            target_table_id varchar(36) NULL,
            table_metadata jsonb NOT NULL,
            table_name varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tableName')) STORED,
            tenant_name varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tenantName')) STORED,
            updatedat int8 NULL GENERATED ALWAYS AS (((table_metadata ->> 'updatedAt')::bigint)) STORED,
            updatedby varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'updatedBy')) STORED,
            deleted boolean NULL GENERATED ALWAYS AS (((table_metadata ->> 'deleted')::boolean)) STORED,
            createdat int8 NULL GENERATED ALWAYS AS (((table_metadata ->> 'createdAt')::bigint)) STORED,
            attributes_metadata jsonb NULL GENERATED ALWAYS AS (((table_metadata ->> 'attributesMetadata')::jsonb)) STORED,
            domain_id varchar(36) NULL GENERATED ALWAYS AS ((table_metadata ->> 'domainId')) STORED,
            tenant_unique_id varchar(36) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tenantUniqueId')) STORED,
            table_metadata_text text NULL GENERATED ALWAYS AS (table_metadata::text) STORED,
            name_description text NULL GENERATED ALWAYS AS (
                ('Table Name: ' ||
                 COALESCE(table_metadata ->> 'tableName', table_metadata ->> 'tablename', '') ||
                 ', Table Description: ' ||
                 COALESCE(table_metadata ->> 'tableDescription', table_metadata ->> 'templateDescription', ''))
            ) STORED,
            dictionary_action char(1) NOT NULL,
            approval_status char(1) NOT NULL DEFAULT 'P',
            current_version_seq integer NULL,
            target_version_seq integer NULL,
            target_version_label varchar(16) NULL GENERATED ALWAYS AS (
                CASE
                    WHEN target_version_seq IS NULL THEN NULL
                    ELSE (target_version_seq::text || '.0')
                END
            ) STORED,
            requester_id varchar(32) NOT NULL,
            requester_ts timestamptz NOT NULL DEFAULT now(),
            approver_id varchar(32) NULL,
            approver_ts timestamptz NULL,
            maker_comment text NULL,
            checker_comment text NULL,
            current_snapshot jsonb NULL,
            validation_errors jsonb NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT table_entity_pending_pkey PRIMARY KEY (pending_id),
            CONSTRAINT table_entity_pending_request_fk FOREIGN KEY (request_id) REFERENCES public.approval_request(request_id),
            CONSTRAINT table_entity_pending_target_fk FOREIGN KEY (target_table_id) REFERENCES public.table_entity(id),
            CONSTRAINT table_entity_pending_dictionary_action_chk CHECK (dictionary_action IN ('A', 'U', 'D')),
            CONSTRAINT table_entity_pending_approval_status_chk CHECK (approval_status IN ('P', 'A', 'R'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.attribute_entity_pending (
            pending_id varchar(36) NOT NULL,
            request_id varchar(36) NOT NULL,
            target_attribute_id varchar(36) NULL,
            metadata jsonb NOT NULL,
            field_name varchar(256) NULL GENERATED ALWAYS AS ((metadata ->> 'Field Name')) STORED,
            table_name varchar(256) NULL GENERATED ALWAYS AS ((metadata ->> 'Table Name')) STORED,
            tenant_name varchar(256) NULL GENERATED ALWAYS AS ((metadata ->> 'tenantName')) STORED,
            updatedat int8 NULL GENERATED ALWAYS AS (((metadata ->> 'updatedAt')::bigint)) STORED,
            updatedby varchar(256) NULL GENERATED ALWAYS AS ((metadata ->> 'updatedBy')) STORED,
            deleted boolean NULL GENERATED ALWAYS AS (((metadata ->> 'deleted')::boolean)) STORED,
            createdat int8 NULL GENERATED ALWAYS AS (((metadata ->> 'createdAt')::bigint)) STORED,
            domain_id varchar(36) NULL GENERATED ALWAYS AS ((metadata ->> 'domainId')) STORED,
            tenant_unique_id varchar(36) NULL GENERATED ALWAYS AS ((metadata ->> 'tenantUniqueId')) STORED,
            tenant_id varchar(36) NULL GENERATED ALWAYS AS ((metadata ->> 'tenantId')) STORED,
            table_id varchar(36) NULL GENERATED ALWAYS AS ((metadata ->> 'tableId')) STORED,
            metadata_text text NULL GENERATED ALWAYS AS (metadata::text) STORED,
            name_description text NULL GENERATED ALWAYS AS (
                ('Field Name: ' ||
                 COALESCE(metadata ->> 'Field Name', '') ||
                 ', Field Description: ' ||
                 COALESCE(metadata ->> 'Field Description', metadata ->> 'fieldDescription', ''))
            ) STORED,
            table_description text NULL GENERATED ALWAYS AS ((metadata ->> 'Table Description')) STORED,
            dictionary_action char(1) NOT NULL,
            approval_status char(1) NOT NULL DEFAULT 'P',
            current_version_seq integer NULL,
            target_version_seq integer NULL,
            target_version_label varchar(16) NULL GENERATED ALWAYS AS (
                CASE
                    WHEN target_version_seq IS NULL THEN NULL
                    ELSE (target_version_seq::text || '.0')
                END
            ) STORED,
            requester_id varchar(32) NOT NULL,
            requester_ts timestamptz NOT NULL DEFAULT now(),
            approver_id varchar(32) NULL,
            approver_ts timestamptz NULL,
            maker_comment text NULL,
            checker_comment text NULL,
            current_snapshot jsonb NULL,
            validation_errors jsonb NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT attribute_entity_pending_pkey PRIMARY KEY (pending_id),
            CONSTRAINT attribute_entity_pending_request_fk FOREIGN KEY (request_id) REFERENCES public.approval_request(request_id),
            CONSTRAINT attribute_entity_pending_target_fk FOREIGN KEY (target_attribute_id) REFERENCES public.attribute_entity(id),
            CONSTRAINT attribute_entity_pending_dictionary_action_chk CHECK (dictionary_action IN ('A', 'U', 'D')),
            CONSTRAINT attribute_entity_pending_approval_status_chk CHECK (approval_status IN ('P', 'A', 'R'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.table_entity_history (
            history_id varchar(36) NOT NULL,
            table_id varchar(36) NOT NULL,
            table_metadata jsonb NOT NULL,
            table_name varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tableName')) STORED,
            tenant_name varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tenantName')) STORED,
            updatedat int8 NULL GENERATED ALWAYS AS (((table_metadata ->> 'updatedAt')::bigint)) STORED,
            updatedby varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'updatedBy')) STORED,
            deleted boolean NULL GENERATED ALWAYS AS (((table_metadata ->> 'deleted')::boolean)) STORED,
            createdat int8 NULL GENERATED ALWAYS AS (((table_metadata ->> 'createdAt')::bigint)) STORED,
            attributes_metadata jsonb NULL GENERATED ALWAYS AS (((table_metadata ->> 'attributesMetadata')::jsonb)) STORED,
            domain_id varchar(36) NULL GENERATED ALWAYS AS ((table_metadata ->> 'domainId')) STORED,
            tenant_unique_id varchar(36) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tenantUniqueId')) STORED,
            table_metadata_text text NULL GENERATED ALWAYS AS (table_metadata::text) STORED,
            name_description text NULL GENERATED ALWAYS AS (
                ('Table Name: ' ||
                 COALESCE(table_metadata ->> 'tableName', table_metadata ->> 'tablename', '') ||
                 ', Table Description: ' ||
                 COALESCE(table_metadata ->> 'tableDescription', table_metadata ->> 'templateDescription', ''))
            ) STORED,
            version_seq integer NOT NULL,
            version_label varchar(16) GENERATED ALWAYS AS ((version_seq::text || '.0')) STORED,
            requester_id varchar(32) NULL,
            approver_id varchar(32) NULL,
            requester_ts timestamptz NULL,
            approver_ts timestamptz NULL,
            dictionary_action char(1) NOT NULL,
            approval_status char(1) NOT NULL DEFAULT 'A',
            record_status char(1) NOT NULL,
            effective_from timestamptz NOT NULL,
            effective_to timestamptz NOT NULL,
            source_request_id varchar(36) NULL,
            archived_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT table_entity_history_pkey PRIMARY KEY (history_id),
            CONSTRAINT table_entity_history_table_fk FOREIGN KEY (table_id) REFERENCES public.table_entity(id),
            CONSTRAINT table_entity_history_request_fk FOREIGN KEY (source_request_id) REFERENCES public.approval_request(request_id),
            CONSTRAINT table_entity_history_dictionary_action_chk CHECK (dictionary_action IN ('A', 'U', 'D')),
            CONSTRAINT table_entity_history_approval_status_chk CHECK (approval_status IN ('A', 'P', 'R')),
            CONSTRAINT table_entity_history_record_status_chk CHECK (record_status IN ('A', 'D')),
            CONSTRAINT table_entity_history_effective_window_chk CHECK (effective_to >= effective_from),
            CONSTRAINT table_entity_history_version_uq UNIQUE (table_id, version_seq)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.attribute_entity_history (
            history_id varchar(36) NOT NULL,
            attribute_id varchar(36) NOT NULL,
            metadata jsonb NOT NULL,
            field_name varchar(256) NULL GENERATED ALWAYS AS ((metadata ->> 'Field Name')) STORED,
            table_name varchar(256) NULL GENERATED ALWAYS AS ((metadata ->> 'Table Name')) STORED,
            tenant_name varchar(256) NULL GENERATED ALWAYS AS ((metadata ->> 'tenantName')) STORED,
            updatedat int8 NULL GENERATED ALWAYS AS (((metadata ->> 'updatedAt')::bigint)) STORED,
            updatedby varchar(256) NULL GENERATED ALWAYS AS ((metadata ->> 'updatedBy')) STORED,
            deleted boolean NULL GENERATED ALWAYS AS (((metadata ->> 'deleted')::boolean)) STORED,
            createdat int8 NULL GENERATED ALWAYS AS (((metadata ->> 'createdAt')::bigint)) STORED,
            domain_id varchar(36) NULL GENERATED ALWAYS AS ((metadata ->> 'domainId')) STORED,
            tenant_unique_id varchar(36) NULL GENERATED ALWAYS AS ((metadata ->> 'tenantUniqueId')) STORED,
            tenant_id varchar(36) NULL GENERATED ALWAYS AS ((metadata ->> 'tenantId')) STORED,
            table_id varchar(36) NULL GENERATED ALWAYS AS ((metadata ->> 'tableId')) STORED,
            metadata_text text NULL GENERATED ALWAYS AS (metadata::text) STORED,
            name_description text NULL GENERATED ALWAYS AS (
                ('Field Name: ' ||
                 COALESCE(metadata ->> 'Field Name', '') ||
                 ', Field Description: ' ||
                 COALESCE(metadata ->> 'Field Description', metadata ->> 'fieldDescription', ''))
            ) STORED,
            table_description text NULL GENERATED ALWAYS AS ((metadata ->> 'Table Description')) STORED,
            version_seq integer NOT NULL,
            version_label varchar(16) GENERATED ALWAYS AS ((version_seq::text || '.0')) STORED,
            requester_id varchar(32) NULL,
            approver_id varchar(32) NULL,
            requester_ts timestamptz NULL,
            approver_ts timestamptz NULL,
            dictionary_action char(1) NOT NULL,
            approval_status char(1) NOT NULL DEFAULT 'A',
            record_status char(1) NOT NULL,
            effective_from timestamptz NOT NULL,
            effective_to timestamptz NOT NULL,
            source_request_id varchar(36) NULL,
            archived_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT attribute_entity_history_pkey PRIMARY KEY (history_id),
            CONSTRAINT attribute_entity_history_attribute_fk FOREIGN KEY (attribute_id) REFERENCES public.attribute_entity(id),
            CONSTRAINT attribute_entity_history_request_fk FOREIGN KEY (source_request_id) REFERENCES public.approval_request(request_id),
            CONSTRAINT attribute_entity_history_dictionary_action_chk CHECK (dictionary_action IN ('A', 'U', 'D')),
            CONSTRAINT attribute_entity_history_approval_status_chk CHECK (approval_status IN ('A', 'P', 'R')),
            CONSTRAINT attribute_entity_history_record_status_chk CHECK (record_status IN ('A', 'D')),
            CONSTRAINT attribute_entity_history_effective_window_chk CHECK (effective_to >= effective_from),
            CONSTRAINT attribute_entity_history_version_uq UNIQUE (attribute_id, version_seq)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.attribute_entity_history")
    op.execute("DROP TABLE IF EXISTS public.table_entity_history")
    op.execute("DROP TABLE IF EXISTS public.attribute_entity_pending")
    op.execute("DROP TABLE IF EXISTS public.table_entity_pending")
