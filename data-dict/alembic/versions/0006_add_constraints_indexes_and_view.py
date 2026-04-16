"""add constraints indexes and dashboard view

Revision ID: mc0006_constraints_view
Revises: mc0005_backfill
Create Date: 2026-04-14
"""
from __future__ import annotations

from alembic import op


revision = "mc0006_constraints_view"
down_revision = "mc0005_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE IF EXISTS public.table_entity
            ALTER COLUMN version_seq SET NOT NULL,
            ALTER COLUMN dictionary_action SET NOT NULL,
            ALTER COLUMN approval_status SET NOT NULL,
            ALTER COLUMN record_status SET NOT NULL,
            ALTER COLUMN effective_from SET NOT NULL
        """
    )
    op.execute(
        """
        ALTER TABLE IF EXISTS public.attribute_entity
            ALTER COLUMN version_seq SET NOT NULL,
            ALTER COLUMN dictionary_action SET NOT NULL,
            ALTER COLUMN approval_status SET NOT NULL,
            ALTER COLUMN record_status SET NOT NULL,
            ALTER COLUMN effective_from SET NOT NULL
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_latest_request_fk') THEN
                ALTER TABLE public.table_entity
                    ADD CONSTRAINT table_entity_latest_request_fk
                    FOREIGN KEY (latest_request_id) REFERENCES public.approval_request(request_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_latest_request_fk') THEN
                ALTER TABLE public.attribute_entity
                    ADD CONSTRAINT attribute_entity_latest_request_fk
                    FOREIGN KEY (latest_request_id) REFERENCES public.approval_request(request_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_dictionary_action_chk') THEN
                ALTER TABLE public.table_entity
                    ADD CONSTRAINT table_entity_dictionary_action_chk
                    CHECK (dictionary_action IN ('A', 'U', 'D'));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_approval_status_chk') THEN
                ALTER TABLE public.table_entity
                    ADD CONSTRAINT table_entity_approval_status_chk
                    CHECK (approval_status IN ('A', 'P', 'R'));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_record_status_chk') THEN
                ALTER TABLE public.table_entity
                    ADD CONSTRAINT table_entity_record_status_chk
                    CHECK (record_status IN ('A', 'D'));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_effective_window_chk') THEN
                ALTER TABLE public.table_entity
                    ADD CONSTRAINT table_entity_effective_window_chk
                    CHECK (effective_to IS NULL OR effective_to >= effective_from);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_dictionary_action_chk') THEN
                ALTER TABLE public.attribute_entity
                    ADD CONSTRAINT attribute_entity_dictionary_action_chk
                    CHECK (dictionary_action IN ('A', 'U', 'D'));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_approval_status_chk') THEN
                ALTER TABLE public.attribute_entity
                    ADD CONSTRAINT attribute_entity_approval_status_chk
                    CHECK (approval_status IN ('A', 'P', 'R'));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_record_status_chk') THEN
                ALTER TABLE public.attribute_entity
                    ADD CONSTRAINT attribute_entity_record_status_chk
                    CHECK (record_status IN ('A', 'D'));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_effective_window_chk') THEN
                ALTER TABLE public.attribute_entity
                    ADD CONSTRAINT attribute_entity_effective_window_chk
                    CHECK (effective_to IS NULL OR effective_to >= effective_from);
            END IF;
        END $$;
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS table_entity_record_status_idx ON public.table_entity (tenant_unique_id, record_status)")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_latest_request_idx ON public.table_entity (latest_request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_version_idx ON public.table_entity (id, version_seq)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_record_status_idx ON public.attribute_entity (table_id, record_status)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_latest_request_idx ON public.attribute_entity (latest_request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_version_idx ON public.attribute_entity (id, version_seq)")

    op.execute("CREATE INDEX IF NOT EXISTS table_entity_pending_request_idx ON public.table_entity_pending (request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_pending_status_requester_idx ON public.table_entity_pending (approval_status, requester_ts DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_pending_tenant_status_idx ON public.table_entity_pending (tenant_unique_id, approval_status)")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_pending_target_status_idx ON public.table_entity_pending (target_table_id, approval_status)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS table_entity_pending_target_pending_uq ON public.table_entity_pending (target_table_id) WHERE approval_status = 'P' AND target_table_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_pending_metadata_text_gin_trgm_idx ON public.table_entity_pending USING gin (table_metadata_text gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_pending_name_description_gin_trgm_idx ON public.table_entity_pending USING gin (name_description gin_trgm_ops)")

    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_pending_request_idx ON public.attribute_entity_pending (request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_pending_table_status_idx ON public.attribute_entity_pending (table_id, approval_status)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_pending_tenant_status_idx ON public.attribute_entity_pending (tenant_unique_id, approval_status)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS attribute_entity_pending_target_pending_uq ON public.attribute_entity_pending (target_attribute_id) WHERE approval_status = 'P' AND target_attribute_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_pending_metadata_text_gin_trgm_idx ON public.attribute_entity_pending USING gin (metadata_text gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_pending_name_description_gin_trgm_idx ON public.attribute_entity_pending USING gin (name_description gin_trgm_ops)")

    op.execute("CREATE INDEX IF NOT EXISTS table_entity_history_table_version_idx ON public.table_entity_history (table_id, version_seq DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_history_tenant_table_idx ON public.table_entity_history (tenant_unique_id, table_name)")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_history_metadata_text_gin_trgm_idx ON public.table_entity_history USING gin (table_metadata_text gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS table_entity_history_name_description_gin_trgm_idx ON public.table_entity_history USING gin (name_description gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_history_attr_version_idx ON public.attribute_entity_history (attribute_id, version_seq DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_history_table_field_idx ON public.attribute_entity_history (table_id, field_name)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_history_metadata_text_gin_trgm_idx ON public.attribute_entity_history USING gin (metadata_text gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS attribute_entity_history_name_description_gin_trgm_idx ON public.attribute_entity_history USING gin (name_description gin_trgm_ops)")

    op.execute(
        """
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
        JOIN public.approval_request r ON r.request_id = p.request_id

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
        JOIN public.approval_request r ON r.request_id = p.request_id
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS public.approval_dashboard_v")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_history_name_description_gin_trgm_idx")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_history_metadata_text_gin_trgm_idx")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_history_table_field_idx")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_history_attr_version_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_history_name_description_gin_trgm_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_history_metadata_text_gin_trgm_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_history_tenant_table_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_history_table_version_idx")

    op.execute("DROP INDEX IF EXISTS public.attribute_entity_pending_name_description_gin_trgm_idx")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_pending_metadata_text_gin_trgm_idx")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_pending_target_pending_uq")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_pending_tenant_status_idx")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_pending_table_status_idx")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_pending_request_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_pending_name_description_gin_trgm_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_pending_metadata_text_gin_trgm_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_pending_target_pending_uq")
    op.execute("DROP INDEX IF EXISTS public.table_entity_pending_target_status_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_pending_tenant_status_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_pending_status_requester_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_pending_request_idx")

    op.execute("DROP INDEX IF EXISTS public.attribute_entity_version_idx")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_latest_request_idx")
    op.execute("DROP INDEX IF EXISTS public.attribute_entity_record_status_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_version_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_latest_request_idx")
    op.execute("DROP INDEX IF EXISTS public.table_entity_record_status_idx")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_effective_window_chk') THEN
                ALTER TABLE public.attribute_entity DROP CONSTRAINT attribute_entity_effective_window_chk;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_record_status_chk') THEN
                ALTER TABLE public.attribute_entity DROP CONSTRAINT attribute_entity_record_status_chk;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_approval_status_chk') THEN
                ALTER TABLE public.attribute_entity DROP CONSTRAINT attribute_entity_approval_status_chk;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_dictionary_action_chk') THEN
                ALTER TABLE public.attribute_entity DROP CONSTRAINT attribute_entity_dictionary_action_chk;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'attribute_entity_latest_request_fk') THEN
                ALTER TABLE public.attribute_entity DROP CONSTRAINT attribute_entity_latest_request_fk;
            END IF;

            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_effective_window_chk') THEN
                ALTER TABLE public.table_entity DROP CONSTRAINT table_entity_effective_window_chk;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_record_status_chk') THEN
                ALTER TABLE public.table_entity DROP CONSTRAINT table_entity_record_status_chk;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_approval_status_chk') THEN
                ALTER TABLE public.table_entity DROP CONSTRAINT table_entity_approval_status_chk;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_dictionary_action_chk') THEN
                ALTER TABLE public.table_entity DROP CONSTRAINT table_entity_dictionary_action_chk;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'table_entity_latest_request_fk') THEN
                ALTER TABLE public.table_entity DROP CONSTRAINT table_entity_latest_request_fk;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        ALTER TABLE IF EXISTS public.attribute_entity
            ALTER COLUMN effective_from DROP NOT NULL,
            ALTER COLUMN record_status DROP NOT NULL,
            ALTER COLUMN approval_status DROP NOT NULL,
            ALTER COLUMN dictionary_action DROP NOT NULL,
            ALTER COLUMN version_seq DROP NOT NULL
        """
    )
    op.execute(
        """
        ALTER TABLE IF EXISTS public.table_entity
            ALTER COLUMN effective_from DROP NOT NULL,
            ALTER COLUMN record_status DROP NOT NULL,
            ALTER COLUMN approval_status DROP NOT NULL,
            ALTER COLUMN dictionary_action DROP NOT NULL,
            ALTER COLUMN version_seq DROP NOT NULL
        """
    )
