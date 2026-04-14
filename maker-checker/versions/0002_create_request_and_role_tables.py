"""create maker-checker request and role tables

Revision ID: 0002_create_request_and_role_tables
Revises: 0001_baseline_existing_schema
Create Date: 2026-04-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_create_request_and_role_tables"
down_revision = "0001_baseline_existing_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_request",
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("domain_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_unique_id", sa.String(length=36), nullable=False),
        sa.Column("submitted_by", sa.String(length=32), nullable=False),
        sa.Column("submitted_by_name", sa.String(length=256), nullable=True),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("maker_comment", sa.Text(), nullable=True),
        sa.Column("request_status", sa.String(length=32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("reviewed_by", sa.String(length=32), nullable=True),
        sa.Column("reviewed_by_name", sa.String(length=256), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("checker_comment", sa.Text(), nullable=True),
        sa.Column("source_file_name", sa.String(length=512), nullable=True),
        sa.Column("source_file_hash", sa.String(length=256), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("approved_items", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("rejected_items", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("source_type IN ('UPLOAD', 'UI')", name="approval_request_source_type_chk"),
        sa.CheckConstraint(
            "request_status IN ('PENDING', 'APPROVED', 'REJECTED', 'PARTIALLY_APPROVED')",
            name="approval_request_status_chk",
        ),
        sa.ForeignKeyConstraint(["domain_id"], ["domain_entity.id"], name="approval_request_domain_fk"),
        sa.ForeignKeyConstraint(["tenant_unique_id"], ["tenant_entity.id"], name="approval_request_tenant_fk"),
        sa.PrimaryKeyConstraint("request_id", name="approval_request_pkey"),
    )
    op.create_table(
        "tenant_role_mapping",
        sa.Column("mapping_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("domain_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_unique_id", sa.String(length=36), nullable=False),
        sa.Column("role_type", sa.String(length=20), nullable=False),
        sa.Column("ad_group_name", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role_type IN ('REQUESTER', 'APPROVER', 'VIEWER')", name="tenant_role_mapping_role_type_chk"),
        sa.ForeignKeyConstraint(["domain_id"], ["domain_entity.id"], name="tenant_role_mapping_domain_fk"),
        sa.ForeignKeyConstraint(["tenant_unique_id"], ["tenant_entity.id"], name="tenant_role_mapping_tenant_fk"),
        sa.PrimaryKeyConstraint("mapping_id", name="tenant_role_mapping_pkey"),
        sa.UniqueConstraint("tenant_unique_id", "role_type", name="tenant_role_mapping_uq"),
    )
    op.create_index("approval_request_tenant_status_submitted_idx", "approval_request", ["tenant_unique_id", "request_status", "submitted_at"], unique=False)
    op.create_index("approval_request_submitter_submitted_idx", "approval_request", ["submitted_by", "submitted_at"], unique=False)
    op.create_index("approval_request_source_file_hash_idx", "approval_request", ["source_file_hash"], unique=False)
    op.create_index("tenant_role_mapping_active_idx", "tenant_role_mapping", ["tenant_unique_id", "role_type", "is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("tenant_role_mapping_active_idx", table_name="tenant_role_mapping")
    op.drop_table("tenant_role_mapping")
    op.drop_index("approval_request_source_file_hash_idx", table_name="approval_request")
    op.drop_index("approval_request_submitter_submitted_idx", table_name="approval_request")
    op.drop_index("approval_request_tenant_status_submitted_idx", table_name="approval_request")
    op.drop_table("approval_request")
