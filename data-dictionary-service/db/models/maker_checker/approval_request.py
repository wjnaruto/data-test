from __future__ import annotations

from .common import Any, Field, Optional, SQLModel, sa


class ApprovalRequest(SQLModel, table=True):
    __tablename__ = "approval_request"
    __table_args__ = (
        sa.CheckConstraint("source_type IN ('UPLOAD', 'UI')", name="approval_request_source_type_chk"),
        sa.CheckConstraint(
            "request_status IN ('PENDING', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'COMPLETED_MIXED')",
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

    request_id: str = Field(primary_key=True, max_length=36, description="Unique maker-checker request id.")
    source_type: str = Field(max_length=20, description="Request source type, either UI or UPLOAD.")
    domain_id: str = Field(foreign_key="domain_entity.id", max_length=36, description="Domain id associated with the request.")
    tenant_unique_id: str = Field(foreign_key="tenant_entity.id", max_length=36, description="Tenant unique id associated with all pending items in the request.")
    submitted_by: str = Field(max_length=32, description="Requester user id that submitted the request.")
    submitted_by_name: Optional[str] = Field(default=None, max_length=256, description="Display name of the requester that submitted the request.")
    submitted_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        description="Timestamp when the request was submitted.",
    )
    maker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True), description="Optional requester comment submitted with the request.")
    request_status: str = Field(
        default="PENDING",
        sa_column=sa.Column(sa.String(length=32), nullable=False, server_default=sa.text("'PENDING'")),
        description="Overall request status: PENDING, IN_REVIEW, APPROVED, REJECTED, or COMPLETED_MIXED.",
    )
    reviewed_by: Optional[str] = Field(default=None, max_length=32, description="Last checker user id that reviewed part or all of the request.")
    reviewed_by_name: Optional[str] = Field(default=None, max_length=256, description="Display name of the last checker that reviewed part or all of the request.")
    reviewed_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True), description="Timestamp of the last review action on this request.")
    checker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True), description="Latest checker comment captured during approve or reject.")
    source_file_name: Optional[str] = Field(default=None, max_length=512, description="Original uploaded file name for bulk upload requests.")
    source_file_hash: Optional[str] = Field(default=None, max_length=256, description="Hash of the uploaded source file for traceability and duplicate checks.")
    total_items: int = Field(default=0, sa_column=sa.Column(sa.Integer(), nullable=False, server_default=sa.text("0")), description="Total number of table and attribute pending items in the request.")
    approved_items: int = Field(default=0, sa_column=sa.Column(sa.Integer(), nullable=False, server_default=sa.text("0")), description="Number of pending items approved so far.")
    rejected_items: int = Field(default=0, sa_column=sa.Column(sa.Integer(), nullable=False, server_default=sa.text("0")), description="Number of pending items rejected so far.")
    created_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        description="Timestamp when the request row was created.",
    )
    updated_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        description="Timestamp when the request row was last updated.",
    )
