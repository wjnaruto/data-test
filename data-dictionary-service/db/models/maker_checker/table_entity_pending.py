from __future__ import annotations

from .common import Any, Field, JSONB, Optional, SQLModel, sa


class TableEntityPending(SQLModel, table=True):
    __tablename__ = "table_entity_pending"
    __table_args__ = (
        sa.CheckConstraint("dictionary_action IN ('A', 'U', 'D')", name="table_entity_pending_dictionary_action_chk"),
        sa.CheckConstraint("approval_status IN ('P', 'A', 'R')", name="table_entity_pending_approval_status_chk"),
        sa.Index("table_entity_pending_request_idx", "request_id"),
        sa.Index("table_entity_pending_status_requester_idx", "approval_status", sa.text("requester_ts DESC")),
        sa.Index("table_entity_pending_tenant_status_idx", "tenant_unique_id", "approval_status"),
        sa.Index("table_entity_pending_target_status_idx", "target_table_id", "approval_status"),
        sa.Index(
            "table_entity_pending_target_pending_uq",
            "target_table_id",
            unique=True,
            postgresql_where=sa.text("approval_status = 'P' AND target_table_id IS NOT NULL"),
        ),
        sa.Index(
            "table_entity_pending_metadata_text_gin_trgm_idx",
            "table_metadata_text",
            postgresql_using="gin",
            postgresql_ops={"table_metadata_text": "gin_trgm_ops"},
        ),
        sa.Index(
            "table_entity_pending_name_description_gin_trgm_idx",
            "name_description",
            postgresql_using="gin",
            postgresql_ops={"name_description": "gin_trgm_ops"},
        ),
    )

    pending_id: str = Field(primary_key=True, max_length=36, description="Unique pending dataset item id.")
    request_id: str = Field(foreign_key="approval_request.request_id", max_length=36, description="Approval request id that groups this pending dataset item.")
    target_table_id: Optional[str] = Field(default=None, foreign_key="table_entity.id", max_length=36, description="Existing dataset id for update/delete actions; null for new dataset additions.")
    table_metadata: dict = Field(default_factory=dict, sa_column=sa.Column(JSONB, nullable=False), description="Proposed dataset metadata JSONB to be reviewed and published on approval.")
    table_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(table_metadata ->> 'tableName')", persisted=True), nullable=True), description="Generated dataset table name extracted from table_metadata.")
    tenant_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(table_metadata ->> 'tenantName')", persisted=True), nullable=True), description="Generated tenant name extracted from table_metadata.")
    updatedat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((table_metadata ->> 'updatedAt')::bigint)", persisted=True), nullable=True), description="Generated updated timestamp extracted from table_metadata.")
    updatedby: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(table_metadata ->> 'updatedBy')", persisted=True), nullable=True), description="Generated updated-by user id extracted from table_metadata.")
    deleted: Optional[bool] = Field(default=None, sa_column=sa.Column(sa.Boolean(), sa.Computed("((table_metadata ->> 'deleted')::boolean)", persisted=True), nullable=True), description="Generated soft-delete flag extracted from table_metadata.")
    createdat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((table_metadata ->> 'createdAt')::bigint)", persisted=True), nullable=True), description="Generated created timestamp extracted from table_metadata.")
    attributes_metadata: Optional[dict] = Field(default=None, sa_column=sa.Column(JSONB, sa.Computed("((table_metadata ->> 'attributesMetadata')::jsonb)", persisted=True), nullable=True), description="Generated attributes metadata extracted from table_metadata when present.")
    domain_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(table_metadata ->> 'domainId')", persisted=True), nullable=True), description="Generated domain id extracted from table_metadata.")
    tenant_unique_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(table_metadata ->> 'tenantUniqueId')", persisted=True), nullable=True), description="Generated tenant unique id extracted from table_metadata.")
    table_metadata_text: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("(table_metadata::text)", persisted=True), nullable=True), description="Generated text representation of table_metadata for full-text search.")
    name_description: Optional[str] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Text(),
            sa.Computed(
                "('Table Name: ' || COALESCE(table_metadata ->> 'tableName', table_metadata ->> 'tablename', '') || ', Table Description: ' || COALESCE(table_metadata ->> 'tableDescription', table_metadata ->> 'templateDescription', ''))",
                persisted=True,
            ),
            nullable=True,
        ),
        description="Generated searchable dataset name and description text.",
    )
    table_description: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("""(table_metadata ->> 'Table Description')""", persisted=True), nullable=True), description="Generated dataset description extracted from table_metadata.")
    dictionary_action: str = Field(sa_column=sa.Column(sa.CHAR(length=1), nullable=False), description="Requested dictionary action: A add, U update, or D delete.")
    approval_status: str = Field(default="P", sa_column=sa.Column(sa.CHAR(length=1), nullable=False, server_default=sa.text("'P'")), description="Item approval status: P pending, A approved, or R rejected.")
    current_version_seq: Optional[int] = Field(default=None, description="Current published version sequence before this pending change.")
    target_version_seq: Optional[int] = Field(default=None, description="Target version sequence to assign if this pending change is approved.")
    target_version_label: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=16), sa.Computed("CASE WHEN target_version_seq IS NULL THEN NULL ELSE (target_version_seq::text || '.0') END", persisted=True), nullable=True), description="Generated version label derived from target_version_seq.")
    requester_id: str = Field(max_length=32, description="Requester user id that submitted this pending dataset item.")
    requester_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), description="Timestamp when this pending dataset item was submitted.")
    approver_id: Optional[str] = Field(default=None, max_length=32, description="Checker user id that approved or rejected this pending dataset item.")
    approver_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True), description="Timestamp when this pending dataset item was approved or rejected.")
    maker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True), description="Requester comment for this pending dataset item.")
    checker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True), description="Checker comment captured during approve or reject.")
    current_snapshot: Optional[dict] = Field(default=None, sa_column=sa.Column(JSONB, nullable=True), description="Snapshot of the current published dataset metadata at submit time.")
    validation_errors: Optional[dict] = Field(default=None, sa_column=sa.Column(JSONB, nullable=True), description="Validation errors captured during submit or review.")
    created_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), description="Timestamp when the pending dataset row was created.")
    updated_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), description="Timestamp when the pending dataset row was last updated.")
