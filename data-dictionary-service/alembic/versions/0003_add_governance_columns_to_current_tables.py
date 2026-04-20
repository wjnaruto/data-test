"""add governance columns to current tables

Revision ID: mc0003_current_cols
Revises: mc0002_req_role
Create Date: 2026-04-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "mc0003_current_cols"
down_revision = "mc0002_req_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("table_entity", "attribute_entity"):
        op.add_column(table_name, sa.Column("requester_id", sa.String(length=32), nullable=True))
        op.add_column(table_name, sa.Column("approver_id", sa.String(length=32), nullable=True))
        op.add_column(table_name, sa.Column("requester_ts", sa.TIMESTAMP(timezone=True), nullable=True))
        op.add_column(table_name, sa.Column("approver_ts", sa.TIMESTAMP(timezone=True), nullable=True))
        op.add_column(table_name, sa.Column("version_seq", sa.Integer(), nullable=True))
        op.add_column(
            table_name,
            sa.Column(
                "version_label",
                sa.String(length=16),
                sa.Computed(
                    "CASE WHEN version_seq IS NULL THEN NULL ELSE (version_seq::text || '.0') END",
                    persisted=True,
                ),
                nullable=True,
            ),
        )
        op.add_column(table_name, sa.Column("dictionary_action", sa.CHAR(length=1), nullable=True))
        op.add_column(table_name, sa.Column("approval_status", sa.CHAR(length=1), nullable=True))
        op.add_column(table_name, sa.Column("record_status", sa.CHAR(length=1), nullable=True))
        op.add_column(table_name, sa.Column("effective_from", sa.TIMESTAMP(timezone=True), nullable=True))
        op.add_column(table_name, sa.Column("effective_to", sa.TIMESTAMP(timezone=True), nullable=True))
        op.add_column(table_name, sa.Column("latest_request_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    for table_name in ("attribute_entity", "table_entity"):
        op.drop_column(table_name, "latest_request_id")
        op.drop_column(table_name, "effective_to")
        op.drop_column(table_name, "effective_from")
        op.drop_column(table_name, "record_status")
        op.drop_column(table_name, "approval_status")
        op.drop_column(table_name, "dictionary_action")
        op.drop_column(table_name, "version_label")
        op.drop_column(table_name, "version_seq")
        op.drop_column(table_name, "approver_ts")
        op.drop_column(table_name, "requester_ts")
        op.drop_column(table_name, "approver_id")
        op.drop_column(table_name, "requester_id")
