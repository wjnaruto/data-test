"""init schema

Revision ID: 0001_init_schema
Revises: 
Create Date: 2026-01-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coordinator_control",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("base_name", sa.String(length=128), nullable=False),
        sa.Column("content_md5", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("instance_id", sa.String(length=100), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index(
        "uniq_processing_per_base_md5",
        "coordinator_control",
        ["base_name", "content_md5"],
        unique=True,
        postgresql_where=sa.text("status = 'processing'"),
    )
    op.create_index("idx_control_file_status", "coordinator_control", ["file_name", "status"])
    op.create_index(
        "idx_control_base_created",
        "coordinator_control",
        ["base_name", sa.text("created_at DESC")],
    )
    op.create_index("idx_control_md5", "coordinator_control", ["content_md5"])
    op.create_index("idx_control_status", "coordinator_control", ["status"])


def downgrade() -> None:
    op.drop_index("idx_control_status", table_name="coordinator_control")
    op.drop_index("idx_control_md5", table_name="coordinator_control")
    op.drop_index("idx_control_base_created", table_name="coordinator_control")
    op.drop_index("idx_control_file_status", table_name="coordinator_control")
    op.drop_index("uniq_processing_per_base_md5", table_name="coordinator_control")
    op.drop_table("coordinator_control")
