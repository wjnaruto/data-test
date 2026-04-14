from __future__ import annotations

from .common import Any, Field, JSONB, Optional, SQLModel, sa


class AttributeEntityHistory(SQLModel, table=True):
    __tablename__ = "attribute_entity_history"
    __table_args__ = (
        sa.CheckConstraint("dictionary_action IN ('A', 'U', 'D')", name="attribute_entity_history_dictionary_action_chk"),
        sa.CheckConstraint("approval_status IN ('A', 'P', 'R')", name="attribute_entity_history_approval_status_chk"),
        sa.CheckConstraint("record_status IN ('A', 'D')", name="attribute_entity_history_record_status_chk"),
        sa.CheckConstraint("effective_to >= effective_from", name="attribute_entity_history_effective_window_chk"),
        sa.UniqueConstraint("attribute_id", "version_seq", name="attribute_entity_history_version_uq"),
        sa.Index("attribute_entity_history_attr_version_idx", "attribute_id", sa.text("version_seq DESC")),
        sa.Index("attribute_entity_history_table_field_idx", "table_id", "field_name"),
        sa.Index(
            "attribute_entity_history_metadata_text_gin_trgm_idx",
            "metadata_text",
            postgresql_using="gin",
            postgresql_ops={"metadata_text": "gin_trgm_ops"},
        ),
        sa.Index(
            "attribute_entity_history_name_description_gin_trgm_idx",
            "name_description",
            postgresql_using="gin",
            postgresql_ops={"name_description": "gin_trgm_ops"},
        ),
    )

    history_id: str = Field(primary_key=True, max_length=36)
    attribute_id: str = Field(foreign_key="attribute_entity.id", max_length=36)
    metadata_json: dict = Field(default_factory=dict, sa_column=sa.Column("metadata", JSONB, nullable=False))
    field_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("""(metadata ->> 'Field Name')""", persisted=True)))
    table_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("""(metadata ->> 'Table Name')""", persisted=True)))
    tenant_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(metadata ->> 'tenantName')", persisted=True)))
    updatedat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((metadata ->> 'updatedAt')::bigint)", persisted=True)))
    updatedby: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(metadata ->> 'updatedBy')", persisted=True)))
    deleted: Optional[bool] = Field(default=None, sa_column=sa.Column(sa.Boolean(), sa.Computed("((metadata ->> 'deleted')::boolean)", persisted=True)))
    createdat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((metadata ->> 'createdAt')::bigint)", persisted=True)))
    domain_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'domainId')", persisted=True)))
    tenant_unique_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tenantUniqueId')", persisted=True)))
    tenant_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tenantId')", persisted=True)))
    table_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tableId')", persisted=True)))
    metadata_text: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("(metadata::text)", persisted=True)))
    name_description: Optional[str] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Text(),
            sa.Computed(
                "('Field Name: ' || COALESCE(metadata ->> 'Field Name', '') || ', Field Description: ' || COALESCE(metadata ->> 'Field Description', metadata ->> 'fieldDescription', ''))",
                persisted=True,
            ),
        ),
    )
    table_description: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("""(metadata ->> 'Table Description')""", persisted=True)))
    version_seq: int = Field(sa_column=sa.Column(sa.Integer(), nullable=False))
    version_label: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=16), sa.Computed("(version_seq::text || '.0')", persisted=True)))
    requester_id: Optional[str] = Field(default=None, max_length=32)
    approver_id: Optional[str] = Field(default=None, max_length=32)
    requester_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True))
    approver_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True))
    dictionary_action: str = Field(sa_column=sa.Column(sa.CHAR(length=1), nullable=False))
    approval_status: str = Field(default="A", sa_column=sa.Column(sa.CHAR(length=1), nullable=False, server_default=sa.text("'A'")))
    record_status: str = Field(sa_column=sa.Column(sa.CHAR(length=1), nullable=False))
    effective_from: Any = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    effective_to: Any = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    source_request_id: Optional[str] = Field(default=None, foreign_key="approval_request.request_id", max_length=36)
    archived_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))

