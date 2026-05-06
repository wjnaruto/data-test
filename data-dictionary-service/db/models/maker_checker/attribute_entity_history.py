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

    history_id: str = Field(primary_key=True, max_length=36, description="Unique attribute history row id.")
    attribute_id: str = Field(foreign_key="attribute_entity.id", max_length=36, description="Published attribute id that this history version belongs to.")
    metadata_json: dict = Field(default_factory=dict, sa_column=sa.Column("metadata", JSONB, nullable=False), description="Archived attribute metadata JSONB for this version.")
    field_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("""(metadata ->> 'Field Name')""", persisted=True)), description="Generated field name extracted from metadata.")
    table_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("""(metadata ->> 'Table Name')""", persisted=True)), description="Generated parent table name extracted from metadata.")
    tenant_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(metadata ->> 'tenantName')", persisted=True)), description="Generated tenant name extracted from metadata.")
    updatedat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((metadata ->> 'updatedAt')::bigint)", persisted=True)), description="Generated updated timestamp extracted from metadata.")
    updatedby: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(metadata ->> 'updatedBy')", persisted=True)), description="Generated updated-by user id extracted from metadata.")
    deleted: Optional[bool] = Field(default=None, sa_column=sa.Column(sa.Boolean(), sa.Computed("((metadata ->> 'deleted')::boolean)", persisted=True)), description="Generated soft-delete flag extracted from metadata.")
    createdat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((metadata ->> 'createdAt')::bigint)", persisted=True)), description="Generated created timestamp extracted from metadata.")
    domain_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'domainId')", persisted=True)), description="Generated domain id extracted from metadata.")
    tenant_unique_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tenantUniqueId')", persisted=True)), description="Generated tenant unique id extracted from metadata.")
    tenant_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tenantId')", persisted=True)), description="Generated tenant id extracted from metadata.")
    table_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(metadata ->> 'tableId')", persisted=True)), description="Generated parent dataset id extracted from metadata.")
    metadata_text: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("(metadata::text)", persisted=True)), description="Generated text representation of metadata for full-text search.")
    name_description: Optional[str] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Text(),
            sa.Computed(
                "('Field Name: ' || COALESCE(metadata ->> 'Field Name', '') || ', Field Description: ' || COALESCE(metadata ->> 'Field Description', metadata ->> 'fieldDescription', ''))",
                persisted=True,
            ),
        ),
        description="Generated searchable attribute name and description text.",
    )
    table_description: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("""(metadata ->> 'Table Description')""", persisted=True)), description="Generated parent dataset description extracted from metadata.")
    version_seq: int = Field(sa_column=sa.Column(sa.Integer(), nullable=False), description="Sequential version number for the attribute record.")
    version_label: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=16), sa.Computed("(version_seq::text || '.0')", persisted=True)), description="Generated version label derived from version_seq.")
    requester_id: Optional[str] = Field(default=None, max_length=32, description="Requester user id associated with the change that created this history version.")
    approver_id: Optional[str] = Field(default=None, max_length=32, description="Checker user id that approved the change that created this history version.")
    requester_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True), description="Timestamp when the requester submitted the change.")
    approver_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True), description="Timestamp when the checker approved the change.")
    dictionary_action: str = Field(sa_column=sa.Column(sa.CHAR(length=1), nullable=False), description="Dictionary action that produced this history version: A add, U update, or D delete.")
    approval_status: str = Field(default="A", sa_column=sa.Column(sa.CHAR(length=1), nullable=False, server_default=sa.text("'A'")), description="Approval status for this history row, normally A after approval.")
    record_status: str = Field(sa_column=sa.Column(sa.CHAR(length=1), nullable=False), description="Record status for this version: A active or D disabled.")
    effective_from: Any = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False), description="Timestamp when this attribute version became effective.")
    effective_to: Any = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False), description="Timestamp when this attribute version stopped being effective.")
    source_request_id: Optional[str] = Field(default=None, foreign_key="approval_request.request_id", max_length=36, description="Approval request id that produced this history version.")
    archived_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), description="Timestamp when this history row was archived.")
