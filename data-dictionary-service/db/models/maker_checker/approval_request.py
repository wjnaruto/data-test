from __future__ import annotations

from .common import Any, Field, Optional, SQLModel, sa


class ApprovalRequest(SQLModel, table=True):
    __tablename__ = "approval_request"
    __table_args__ = (
        sa.CheckConstraint("source_type IN ('UPLOAD', 'UI')", name="approval_request_source_type_chk"),
        sa.CheckConstraint(
            "request_status IN ('PENDING', 'APPROVED', 'REJECTED', 'PARTIALLY_APPROVED')",
            name="approval_request_status_chk",
        ),
        sa.Index(
            "approval_request_tenant_status_submitted_idx",
            "tenant_unique_id",
            "request_status",
            "submitted_at",
        ),
        sa.Index("approval_request_submitter_submitted_idx", "submitted_by", "submitted_at"),
        sa.Index("approval_request_source_file_hash_idx", "source_file_hash"),
    )

    request_id: str = Field(primary_key=True, max_length=36)
    source_type: str = Field(max_length=20)
    domain_id: str = Field(foreign_key="domain_entity.id", max_length=36)
    tenant_unique_id: str = Field(foreign_key="tenant_entity.id", max_length=36)
    submitted_by: str = Field(max_length=32)
    submitted_by_name: Optional[str] = Field(default=None, max_length=256)
    submitted_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    maker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True))
    request_status: str = Field(
        default="PENDING",
        sa_column=sa.Column(sa.String(length=32), nullable=False, server_default=sa.text("'PENDING'")),
    )
    reviewed_by: Optional[str] = Field(default=None, max_length=32)
    reviewed_by_name: Optional[str] = Field(default=None, max_length=256)
    reviewed_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True))
    checker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True))
    source_file_name: Optional[str] = Field(default=None, max_length=512)
    source_file_hash: Optional[str] = Field(default=None, max_length=256)
    total_items: int = Field(default=0, sa_column=sa.Column(sa.Integer(), nullable=False, server_default=sa.text("0")))
    approved_items: int = Field(default=0, sa_column=sa.Column(sa.Integer(), nullable=False, server_default=sa.text("0")))
    rejected_items: int = Field(default=0, sa_column=sa.Column(sa.Integer(), nullable=False, server_default=sa.text("0")))
    created_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    updated_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

