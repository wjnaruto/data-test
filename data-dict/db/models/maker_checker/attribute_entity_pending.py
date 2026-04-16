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

    pending_id: str = Field(primary_key=True, max_length=36)
    request_id: str = Field(foreign_key="approval_request.request_id", max_length=36)
    target_attribute_id: Optional[str] = Field(default=None, foreign_key="attribute_entity.id", max_length=36)
    metadata_json: dict = Field(default_factory=dict, sa_column=sa.Column("metadata", JSONB, nullable=False))
    field_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("""(metadata ->> 'Field Name')""", persisted=True), nullable=True))
    table_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("""(metadata ->> 'Table Name')""", persisted=True), nullable=True))
    tenant_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(metadata ->> 'tenantName')", persisted=True), nullable=True))
    updatedat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((metadata ->> 'updatedAt')::bigint)", persisted=True), nullable=True))
    updatedby: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(metadata ->> 'updatedBy')", persisted=True), nullable=True))
    deleted: Optional[bool] = Field(default=None, sa_column=sa.Column(sa.Boolean(), sa.Computed("((metadata ->> 'deleted')::boolean)", persisted=True), nullable=True))
    createdat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((metadata ->> 'createdAt')::bigint)", persisted=True), nullable=True))
    domain_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'domainId')", persisted=True), nullable=True))
    tenant_unique_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tenantUniqueId')", persisted=True), nullable=True))
    tenant_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tenantId')", persisted=True), nullable=True))
    table_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tableId')", persisted=True), nullable=True))
    metadata_text: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("(metadata::text)", persisted=True), nullable=True))
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
    )
    table_description: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("""(metadata ->> 'Table Description')""", persisted=True), nullable=True))
    dictionary_action: str = Field(sa_column=sa.Column(sa.CHAR(length=1), nullable=False))
    approval_status: str = Field(default="P", sa_column=sa.Column(sa.CHAR(length=1), nullable=False, server_default=sa.text("'P'")))
    current_version_seq: Optional[int] = Field(default=None)
    target_version_seq: Optional[int] = Field(default=None)
    target_version_label: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=16), sa.Computed("CASE WHEN target_version_seq IS NULL THEN NULL ELSE (target_version_seq::text || '.0') END", persisted=True), nullable=True))
    requester_id: str = Field(max_length=32)
    requester_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    approver_id: Optional[str] = Field(default=None, max_length=32)
    approver_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True))
    maker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True))
    checker_comment: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True))
    current_snapshot: Optional[dict] = Field(default=None, sa_column=sa.Column(JSONB, nullable=True))
    validation_errors: Optional[dict] = Field(default=None, sa_column=sa.Column(JSONB, nullable=True))
    created_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    updated_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))

