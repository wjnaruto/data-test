"""baseline existing production schema

Revision ID: 0001_baseline_existing_schema
Revises:
Create Date: 2026-04-14
"""
from __future__ import annotations


revision = "0001_baseline_existing_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is an intentional no-op baseline revision.
    # Existing environments should be stamped to this revision:
    #   alembic -c alembic.ini stamp 0001_baseline_existing_schema
    pass


def downgrade() -> None:
    pass
