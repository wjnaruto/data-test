"""update approval request review statuses

Revision ID: mc0007_review_statuses
Revises: mc0006_constraints_view
Create Date: 2026-05-05
"""
from __future__ import annotations

from alembic import op


revision = "mc0007_review_statuses"
down_revision = "mc0006_constraints_view"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE public.approval_request
        SET request_status = 'IN_REVIEW'
        WHERE request_status = 'PARTIALLY_APPROVED'
        """
    )
    op.execute(
        """
        ALTER TABLE public.approval_request
        DROP CONSTRAINT IF EXISTS approval_request_status_chk
        """
    )
    op.execute(
        """
        ALTER TABLE public.approval_request
        ADD CONSTRAINT approval_request_status_chk
        CHECK (request_status IN ('PENDING', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'COMPLETED_MIXED'))
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE public.approval_request
        SET request_status = 'PARTIALLY_APPROVED'
        WHERE request_status IN ('IN_REVIEW', 'COMPLETED_MIXED')
        """
    )
    op.execute(
        """
        ALTER TABLE public.approval_request
        DROP CONSTRAINT IF EXISTS approval_request_status_chk
        """
    )
    op.execute(
        """
        ALTER TABLE public.approval_request
        ADD CONSTRAINT approval_request_status_chk
        CHECK (request_status IN ('PENDING', 'APPROVED', 'REJECTED', 'PARTIALLY_APPROVED'))
        """
    )
