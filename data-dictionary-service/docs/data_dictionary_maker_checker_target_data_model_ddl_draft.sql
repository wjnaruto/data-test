-- Draft PostgreSQL DDL for Data Dictionary Service Maker-Checker enhancement
-- Assumptions:
-- 1. Existing current published tables remain:
--    - public.domain_entity
--    - public.tenant_entity
--    - public.table_entity        -- business meaning: dataset
--    - public.attribute_entity
-- 2. Existing IDs remain varchar(36) for consistency with the current model.
-- 3. Existing jsonb + generated stored columns pattern is retained.
-- 4. This file is a design draft. It should be adapted into Alembic migrations rather than executed as-is in production.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =========================================================
-- 1. Approval request header
-- =========================================================

CREATE TABLE IF NOT EXISTS public.approval_request (
    request_id varchar(36) NOT NULL,
    source_type varchar(20) NOT NULL,
    domain_id varchar(36) NOT NULL,
    tenant_unique_id varchar(36) NOT NULL,
    submitted_by varchar(32) NOT NULL,
    submitted_by_name varchar(256) NULL,
    submitted_at timestamptz NOT NULL DEFAULT now(),
    maker_comment text NULL,
    request_status varchar(32) NOT NULL DEFAULT 'PENDING',
    reviewed_by varchar(32) NULL,
    reviewed_by_name varchar(256) NULL,
    reviewed_at timestamptz NULL,
    checker_comment text NULL,
    source_file_name varchar(512) NULL,
    source_file_hash varchar(256) NULL,
    total_items integer NOT NULL DEFAULT 0,
    approved_items integer NOT NULL DEFAULT 0,
    rejected_items integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT approval_request_pkey PRIMARY KEY (request_id),
    CONSTRAINT approval_request_source_type_chk CHECK (source_type IN ('UPLOAD', 'UI')),
    CONSTRAINT approval_request_status_chk CHECK (request_status IN ('PENDING', 'APPROVED', 'REJECTED', 'PARTIALLY_APPROVED')),
    CONSTRAINT approval_request_domain_fk FOREIGN KEY (domain_id) REFERENCES public.domain_entity(id),
    CONSTRAINT approval_request_tenant_fk FOREIGN KEY (tenant_unique_id) REFERENCES public.tenant_entity(id)
);

CREATE INDEX IF NOT EXISTS approval_request_tenant_status_submitted_idx
    ON public.approval_request (tenant_unique_id, request_status, submitted_at DESC);

CREATE INDEX IF NOT EXISTS approval_request_submitter_submitted_idx
    ON public.approval_request (submitted_by, submitted_at DESC);

CREATE INDEX IF NOT EXISTS approval_request_source_file_hash_idx
    ON public.approval_request (source_file_hash);

-- =========================================================
-- 2. Tenant role mapping
-- =========================================================

CREATE TABLE IF NOT EXISTS public.tenant_role_mapping (
    mapping_id bigint GENERATED ALWAYS AS IDENTITY,
    domain_id varchar(36) NOT NULL,
    tenant_unique_id varchar(36) NOT NULL,
    role_type varchar(20) NOT NULL,
    ad_group_name varchar(256) NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT tenant_role_mapping_pkey PRIMARY KEY (mapping_id),
    CONSTRAINT tenant_role_mapping_role_type_chk CHECK (role_type IN ('REQUESTER', 'APPROVER', 'VIEWER')),
    CONSTRAINT tenant_role_mapping_domain_fk FOREIGN KEY (domain_id) REFERENCES public.domain_entity(id),
    CONSTRAINT tenant_role_mapping_tenant_fk FOREIGN KEY (tenant_unique_id) REFERENCES public.tenant_entity(id),
    CONSTRAINT tenant_role_mapping_uq UNIQUE (tenant_unique_id, role_type)
);

CREATE INDEX IF NOT EXISTS tenant_role_mapping_active_idx
    ON public.tenant_role_mapping (tenant_unique_id, role_type, is_active);

-- =========================================================
-- 3. Current published dataset table changes
-- =========================================================

ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS requester_id varchar(32);
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS approver_id varchar(32);
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS requester_ts timestamptz;
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS approver_ts timestamptz;
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS version_seq integer;
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS version_label varchar(16) GENERATED ALWAYS AS (
        CASE
            WHEN version_seq IS NULL THEN NULL
            ELSE (version_seq::text || '.0')
        END
    ) STORED;
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS dictionary_action char(1);
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS approval_status char(1);
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS record_status char(1);
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS effective_from timestamptz;
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS effective_to timestamptz;
ALTER TABLE IF EXISTS public.table_entity
    ADD COLUMN IF NOT EXISTS latest_request_id varchar(36);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'table_entity_latest_request_fk'
    ) THEN
        ALTER TABLE public.table_entity
            ADD CONSTRAINT table_entity_latest_request_fk
            FOREIGN KEY (latest_request_id) REFERENCES public.approval_request(request_id);
    END IF;
END $$;

UPDATE public.table_entity
SET
    version_seq = COALESCE(version_seq, 1),
    dictionary_action = COALESCE(dictionary_action, CASE WHEN COALESCE(deleted, false) THEN 'D' ELSE 'A' END),
    approval_status = COALESCE(approval_status, 'A'),
    record_status = COALESCE(record_status, CASE WHEN COALESCE(deleted, false) THEN 'D' ELSE 'A' END),
    effective_from = COALESCE(
        effective_from,
        CASE
            WHEN createdat IS NULL THEN now()
            WHEN createdat > 100000000000 THEN to_timestamp(createdat / 1000.0)
            ELSE to_timestamp(createdat)
        END
    )
WHERE
    version_seq IS NULL
    OR dictionary_action IS NULL
    OR approval_status IS NULL
    OR record_status IS NULL
    OR effective_from IS NULL;

ALTER TABLE IF EXISTS public.table_entity
    ALTER COLUMN version_seq SET NOT NULL;
ALTER TABLE IF EXISTS public.table_entity
    ALTER COLUMN dictionary_action SET NOT NULL;
ALTER TABLE IF EXISTS public.table_entity
    ALTER COLUMN approval_status SET NOT NULL;
ALTER TABLE IF EXISTS public.table_entity
    ALTER COLUMN record_status SET NOT NULL;
ALTER TABLE IF EXISTS public.table_entity
    ALTER COLUMN effective_from SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_dictionary_action_chk'
    ) THEN
        ALTER TABLE public.table_entity
            ADD CONSTRAINT table_entity_dictionary_action_chk
            CHECK (dictionary_action IN ('A', 'U', 'D')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_approval_status_chk'
    ) THEN
        ALTER TABLE public.table_entity
            ADD CONSTRAINT table_entity_approval_status_chk
            CHECK (approval_status IN ('A', 'P', 'R')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_record_status_chk'
    ) THEN
        ALTER TABLE public.table_entity
            ADD CONSTRAINT table_entity_record_status_chk
            CHECK (record_status IN ('A', 'D')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_effective_window_chk'
    ) THEN
        ALTER TABLE public.table_entity
            ADD CONSTRAINT table_entity_effective_window_chk
            CHECK (effective_to IS NULL OR effective_to >= effective_from) NOT VALID;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS table_entity_record_status_idx
    ON public.table_entity (tenant_unique_id, record_status);

CREATE INDEX IF NOT EXISTS table_entity_latest_request_idx
    ON public.table_entity (latest_request_id);

CREATE INDEX IF NOT EXISTS table_entity_version_idx
    ON public.table_entity (id, version_seq);

-- =========================================================
-- 4. Current published attribute table changes
-- =========================================================

ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS requester_id varchar(32);
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS approver_id varchar(32);
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS requester_ts timestamptz;
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS approver_ts timestamptz;
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS version_seq integer;
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS version_label varchar(16) GENERATED ALWAYS AS (
        CASE
            WHEN version_seq IS NULL THEN NULL
            ELSE (version_seq::text || '.0')
        END
    ) STORED;
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS dictionary_action char(1);
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS approval_status char(1);
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS record_status char(1);
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS effective_from timestamptz;
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS effective_to timestamptz;
ALTER TABLE IF EXISTS public.attribute_entity
    ADD COLUMN IF NOT EXISTS latest_request_id varchar(36);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'attribute_entity_latest_request_fk'
    ) THEN
        ALTER TABLE public.attribute_entity
            ADD CONSTRAINT attribute_entity_latest_request_fk
            FOREIGN KEY (latest_request_id) REFERENCES public.approval_request(request_id);
    END IF;
END $$;

UPDATE public.attribute_entity
SET
    version_seq = COALESCE(version_seq, 1),
    dictionary_action = COALESCE(dictionary_action, CASE WHEN COALESCE(deleted, false) THEN 'D' ELSE 'A' END),
    approval_status = COALESCE(approval_status, 'A'),
    record_status = COALESCE(record_status, CASE WHEN COALESCE(deleted, false) THEN 'D' ELSE 'A' END),
    effective_from = COALESCE(
        effective_from,
        CASE
            WHEN createdat IS NULL THEN now()
            WHEN createdat > 100000000000 THEN to_timestamp(createdat / 1000.0)
            ELSE to_timestamp(createdat)
        END
    )
WHERE
    version_seq IS NULL
    OR dictionary_action IS NULL
    OR approval_status IS NULL
    OR record_status IS NULL
    OR effective_from IS NULL;

ALTER TABLE IF EXISTS public.attribute_entity
    ALTER COLUMN version_seq SET NOT NULL;
ALTER TABLE IF EXISTS public.attribute_entity
    ALTER COLUMN dictionary_action SET NOT NULL;
ALTER TABLE IF EXISTS public.attribute_entity
    ALTER COLUMN approval_status SET NOT NULL;
ALTER TABLE IF EXISTS public.attribute_entity
    ALTER COLUMN record_status SET NOT NULL;
ALTER TABLE IF EXISTS public.attribute_entity
    ALTER COLUMN effective_from SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_dictionary_action_chk'
    ) THEN
        ALTER TABLE public.attribute_entity
            ADD CONSTRAINT attribute_entity_dictionary_action_chk
            CHECK (dictionary_action IN ('A', 'U', 'D')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_approval_status_chk'
    ) THEN
        ALTER TABLE public.attribute_entity
            ADD CONSTRAINT attribute_entity_approval_status_chk
            CHECK (approval_status IN ('A', 'P', 'R')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_record_status_chk'
    ) THEN
        ALTER TABLE public.attribute_entity
            ADD CONSTRAINT attribute_entity_record_status_chk
            CHECK (record_status IN ('A', 'D')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_effective_window_chk'
    ) THEN
        ALTER TABLE public.attribute_entity
            ADD CONSTRAINT attribute_entity_effective_window_chk
            CHECK (effective_to IS NULL OR effective_to >= effective_from) NOT VALID;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS attribute_entity_record_status_idx
    ON public.attribute_entity (table_id, record_status);

CREATE INDEX IF NOT EXISTS attribute_entity_latest_request_idx
    ON public.attribute_entity (latest_request_id);

CREATE INDEX IF NOT EXISTS attribute_entity_version_idx
    ON public.attribute_entity (id, version_seq);

-- =========================================================
-- 5. Pending dataset table
-- =========================================================

CREATE TABLE IF NOT EXISTS public.table_entity_pending (
    pending_id varchar(36) NOT NULL,
    request_id varchar(36) NOT NULL,
    target_table_id varchar(36) NULL,
    table_metadata jsonb NOT NULL,
    table_name varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tableName')) STORED,
    tenant_name varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tenantName')) STORED,
    updatedat int8 NULL GENERATED ALWAYS AS (((table_metadata ->> 'updatedat')::bigint)) STORED,
    updatedby varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'updatedBy')) STORED,
    deleted boolean NULL GENERATED ALWAYS AS (((table_metadata ->> 'deleted')::boolean)) STORED,
    createdat int8 NULL GENERATED ALWAYS AS (((table_metadata ->> 'createdat')::bigint)) STORED,
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
);

CREATE INDEX IF NOT EXISTS table_entity_pending_request_idx
    ON public.table_entity_pending (request_id);

CREATE INDEX IF NOT EXISTS table_entity_pending_status_requester_idx
    ON public.table_entity_pending (approval_status, requester_ts DESC);

CREATE INDEX IF NOT EXISTS table_entity_pending_tenant_status_idx
    ON public.table_entity_pending (tenant_unique_id, approval_status);

CREATE INDEX IF NOT EXISTS table_entity_pending_target_status_idx
    ON public.table_entity_pending (target_table_id, approval_status);

CREATE UNIQUE INDEX IF NOT EXISTS table_entity_pending_target_pending_uq
    ON public.table_entity_pending (target_table_id)
    WHERE approval_status = 'P' AND target_table_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS table_entity_pending_metadata_text_gin_trgm_idx
    ON public.table_entity_pending USING gin (table_metadata_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS table_entity_pending_name_description_gin_trgm_idx
    ON public.table_entity_pending USING gin (name_description gin_trgm_ops);

-- =========================================================
-- 6. Pending attribute table
-- =========================================================

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
);

CREATE INDEX IF NOT EXISTS attribute_entity_pending_request_idx
    ON public.attribute_entity_pending (request_id);

CREATE INDEX IF NOT EXISTS attribute_entity_pending_table_status_idx
    ON public.attribute_entity_pending (table_id, approval_status);

CREATE INDEX IF NOT EXISTS attribute_entity_pending_tenant_status_idx
    ON public.attribute_entity_pending (tenant_unique_id, approval_status);

CREATE UNIQUE INDEX IF NOT EXISTS attribute_entity_pending_target_pending_uq
    ON public.attribute_entity_pending (target_attribute_id)
    WHERE approval_status = 'P' AND target_attribute_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS attribute_entity_pending_metadata_text_gin_trgm_idx
    ON public.attribute_entity_pending USING gin (metadata_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS attribute_entity_pending_name_description_gin_trgm_idx
    ON public.attribute_entity_pending USING gin (name_description gin_trgm_ops);

-- =========================================================
-- 7. Dataset history table
-- =========================================================

CREATE TABLE IF NOT EXISTS public.table_entity_history (
    history_id varchar(36) NOT NULL,
    table_id varchar(36) NOT NULL,
    table_metadata jsonb NOT NULL,
    table_name varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tableName')) STORED,
    tenant_name varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'tenantName')) STORED,
    updatedat int8 NULL GENERATED ALWAYS AS (((table_metadata ->> 'updatedat')::bigint)) STORED,
    updatedby varchar(256) NULL GENERATED ALWAYS AS ((table_metadata ->> 'updatedBy')) STORED,
    deleted boolean NULL GENERATED ALWAYS AS (((table_metadata ->> 'deleted')::boolean)) STORED,
    createdat int8 NULL GENERATED ALWAYS AS (((table_metadata ->> 'createdat')::bigint)) STORED,
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
);

CREATE INDEX IF NOT EXISTS table_entity_history_table_version_idx
    ON public.table_entity_history (table_id, version_seq DESC);

CREATE INDEX IF NOT EXISTS table_entity_history_tenant_table_idx
    ON public.table_entity_history (tenant_unique_id, table_name);

CREATE INDEX IF NOT EXISTS table_entity_history_metadata_text_gin_trgm_idx
    ON public.table_entity_history USING gin (table_metadata_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS table_entity_history_name_description_gin_trgm_idx
    ON public.table_entity_history USING gin (name_description gin_trgm_ops);

-- =========================================================
-- 8. Attribute history table
-- =========================================================

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
);

CREATE INDEX IF NOT EXISTS attribute_entity_history_attr_version_idx
    ON public.attribute_entity_history (attribute_id, version_seq DESC);

CREATE INDEX IF NOT EXISTS attribute_entity_history_table_field_idx
    ON public.attribute_entity_history (table_id, field_name);

CREATE INDEX IF NOT EXISTS attribute_entity_history_metadata_text_gin_trgm_idx
    ON public.attribute_entity_history USING gin (metadata_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS attribute_entity_history_name_description_gin_trgm_idx
    ON public.attribute_entity_history USING gin (name_description gin_trgm_ops);

-- =========================================================
-- 9. Unified dashboard view
-- =========================================================

CREATE OR REPLACE VIEW public.approval_dashboard_v AS
SELECT
    r.request_id,
    r.source_type,
    r.request_status,
    r.domain_id,
    r.tenant_unique_id,
    r.submitted_by,
    r.submitted_by_name,
    r.submitted_at,
    r.reviewed_by,
    r.reviewed_by_name,
    r.reviewed_at,
    'DATASET'::varchar(32) AS entity_type,
    COALESCE(p.target_table_id, p.pending_id) AS entity_id,
    p.target_table_id AS target_entity_id,
    p.table_name AS entity_name,
    p.dictionary_action,
    p.approval_status,
    p.current_version_seq,
    p.target_version_seq,
    p.requester_id,
    p.requester_ts,
    p.approver_id,
    p.approver_ts,
    p.maker_comment,
    p.checker_comment,
    p.validation_errors
FROM public.table_entity_pending p
JOIN public.approval_request r
    ON r.request_id = p.request_id

UNION ALL

SELECT
    r.request_id,
    r.source_type,
    r.request_status,
    r.domain_id,
    r.tenant_unique_id,
    r.submitted_by,
    r.submitted_by_name,
    r.submitted_at,
    r.reviewed_by,
    r.reviewed_by_name,
    r.reviewed_at,
    'ATTRIBUTE'::varchar(32) AS entity_type,
    COALESCE(p.target_attribute_id, p.pending_id) AS entity_id,
    p.target_attribute_id AS target_entity_id,
    p.field_name AS entity_name,
    p.dictionary_action,
    p.approval_status,
    p.current_version_seq,
    p.target_version_seq,
    p.requester_id,
    p.requester_ts,
    p.approver_id,
    p.approver_ts,
    p.maker_comment,
    p.checker_comment,
    p.validation_errors
FROM public.attribute_entity_pending p
JOIN public.approval_request r
    ON r.request_id = p.request_id;

