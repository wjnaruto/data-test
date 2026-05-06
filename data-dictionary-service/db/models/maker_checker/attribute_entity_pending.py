from __future__ import annotations

from .common import Any, Field, JSONB, Optional, SQLModel, sa


class AttributeEntityPending(SQLModel, table=True):
    __tablename__ = "attribute_entity_pending"
    __table_args__ = (
        sa.CheckConstraint("dictionary_action IN ('A', 'U', 'D')", name="attribute_entity_pending_dictionary_action_chk"),
        sa.CheckConstraint("approval_status IN ('P', 'A', 'R')", name="attribute_entity_pending_approval_status_chk"),
        sa.Index("attribute_entity_pending_request_idx", "request_id"),
        sa.Index("attribute_entity_pending_table_status_idx", "table_id", "approval_status"),
        sa.Index("attribute_entity_pending_tenant_status_idx", "tenant_unique_id", "approval_status"),
        sa.Index(
            "attribute_entity_pending_target_pending_uq",
            "target_attribute_id",
            unique=True,
            postgresql_where=sa.text("approval_status = 'P' AND target_attribute_id IS NOT NULL"),
        ),
        sa.Index(
            "attribute_entity_pending_metadata_text_gin_trgm_idx",
            "metadata_text",
            postgresql_using="gin",
            postgresql_ops={"metadata_text": "gin_trgm_ops"},
        ),
        sa.Index(
            "attribute_entity_pending_name_description_gin_trgm_idx",
            "name_description",
            postgresql_using="gin",
            postgresql_ops={"name_description": "gin_trgm_ops"},
        ),
    )

    pending_id: str = Field(primary_key=True, max_length=36, description="Unique pending attribute item id.")
    request_id: str = Field(foreign_key="approval_request.request_id", max_length=36, description="Approval request id that groups this pending attribute item.")
    target_attribute_id: Optional[str] = Field(default=None, foreign_key="attribute_entity.id", max_length=36, description="Existing attribute id for update/delete actions; null for new attribute additions.")
    metadata_json: dict = Field(default_factory=dict, sa_column=sa.Column("metadata", JSONB, nullable=False), description="Proposed attribute metadata JSONB to be reviewed and published on approval.")
    field_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("""(metadata ->> 'Field Name')""", persisted=True), nullable=True), description="Generated field name extracted from metadata.")
    table_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("""(metadata ->> 'Table Name')""", persisted=True), nullable=True), description="Generated parent table name extracted from metadata.")
    tenant_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(metadata ->> 'tenantName')", persisted=True), nullable=True), description="Generated tenant name extracted from metadata.")
    updatedat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((metadata ->> 'updatedAt')::bigint)", persisted=True), nullable=True), description="Generated updated timestamp extracted from metadata.")
    updatedby: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(metadata ->> 'updatedBy')", persisted=True), nullable=True), description="Generated updated-by user id extracted from metadata.")
    deleted: Optional[bool] = Field(default=None, sa_column=sa.Column(sa.Boolean(), sa.Computed("((metadata ->> 'deleted')::boolean)", persisted=True), nullable=True), description="Generated soft-delete flag extracted from metadata.")
    createdat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((metadata ->> 'createdAt')::bigint)", persisted=True), nullable=True), description="Generated created timestamp extracted from metadata.")
    domain_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'domainId')", persisted=True), nullable=True), description="Generated domain id extracted from metadata.")
    tenant_unique_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tenantUniqueId')", persisted=True), nullable=True), description="Generated tenant unique id extracted from metadata.")
    tenant_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tenantId')", persisted=True), nullable=True), description="Generated tenant id extracted from metadata.")
    table_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tableId')", persisted=True), nullable=True), description="Generated parent dataset id extracted from metadata.")
    metadata_text: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("(metadata::text)", persisted=True), nullable=True), description="Generated text representation of metadata for full-text search.")
    name_description: Optional[str] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Text(),
            sa.Computed(
                "('Field Name: ' || COALESCE(metadata ->> 'Field Name', '') || ', Field Description: ' || COALESCE(metadata ->> 'Field Description', metadata ->> 'fieldDescription', ''))",
                persisted=True,
            ),
            nullable=True,
        ),
        description="Generated searchable attribute name and description text.",
    )
    table_description: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("""(metadata ->> 'Table Description')""", persisted=True), nullable=True), description="Generated parent dataset description extracted from metadata.")
    dictionary_action: str = Field(sa_column=sa.Column(sa.CHAR(length=1), nullable=False), description="Requested dictionary action: A add, U update, or D delete.")
    approval_status: str = Field(default="P", sa_column=sa.Column(sa.CHAR(length=1), nullable=False, server_default=sa.text("'P'")), description="Item approval status: P pending, A approved, or R rejected.")
    current_version_seq: Optional[int] = Field(default=None, description="Current published version sequence before this pending change.")
    target_version_seq: Optional[int] = Field(default=None, description="Target version sequence to assign if this pending change is approved.")
    target_version_label: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=16), sa.Computed("CASE WHEN target_version_seq IS NULL THEN NULL ELSE (target_version_seq::text || '.0') END", persisted=True), nullable=True), description="Generated version label derived from target_version_seq.")
    requester_id: str = Field(max_length=32, description="Requester user id that submitted this pending attribute item.")
    requester_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), description="Timestamp when this pending attribute item was submitted.")
    approver_id: Optional[str] = Field(default=None, max_length=32, description="Checker user id that approved or rejected this pending attribute item.")
    approver_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True), description="Timestamp when this pending attribute item was approved or rejected.")
    maker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True), description="Requester comment for this pending attribute item.")
    checker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True), description="Checker comment captured during approve or reject.")
    current_snapshot: Optional[dict] = Field(default=None, sa_column=sa.Column(JSONB, nullable=True), description="Snapshot of the current published attribute metadata at submit time.")
    validation_errors: Optional[dict] = Field(default=None, sa_column=sa.Column(JSONB, nullable=True), description="Validation errors captured during submit or review.")
    created_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), description="Timestamp when the pending attribute row was created.")
    updated_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), description="Timestamp when the pending attribute row was last updated.")
