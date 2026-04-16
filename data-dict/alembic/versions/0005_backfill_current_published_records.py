"""backfill governance fields for existing published records

Revision ID: mc0005_backfill
Revises: mc0004_pending_hist
Create Date: 2026-04-14
"""
from __future__ import annotations

from alembic import op


revision = "mc0005_backfill"
down_revision = "mc0004_pending_hist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
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
            OR effective_from IS NULL
        """
    )
    op.execute(
        """
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
            OR effective_from IS NULL
        """
    )


def downgrade() -> None:
    # Intentionally non-destructive.
    # Existing production rows should not be blindly reset after backfill.
    pass
