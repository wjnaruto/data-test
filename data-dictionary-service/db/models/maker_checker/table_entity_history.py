from __future__ import annotations

from .common import Any, Field, JSONB, Optional, SQLModel, sa


class TableEntityHistory(SQLModel, table=True):
    __tablename__ = "table_entity_history"
    __table_args__ = (
        sa.CheckConstraint("dictionary_action IN ('A', 'U', 'D')", name="table_entity_history_dictionary_action_chk"),
        sa.CheckConstraint("approval_status IN ('A', 'P', 'R')", name="table_entity_history_approval_status_chk"),
        sa.CheckConstraint("record_status IN ('A', 'D')", name="table_entity_history_record_status_chk"),
        sa.CheckConstraint("effective_to >= effective_from", name="table_entity_history_effective_window_chk"),
        sa.UniqueConstraint("table_id", "version_seq", name="table_entity_history_version_uq"),
        sa.Index("table_entity_history_table_version_idx", "table_id", sa.text("version_seq DESC")),
        sa.Index("table_entity_history_tenant_table_idx", "tenant_unique_id", "table_name"),
        sa.Index(
            "table_entity_history_metadata_text_gin_trgm_idx",
            "table_metadata_text",
            postgresql_using="gin",
            postgresql_ops={"table_metadata_text": "gin_trgm_ops"},
        ),
        sa.Index(
            "table_entity_history_name_description_gin_trgm_idx",
            "name_description",
            postgresql_using="gin",
            postgresql_ops={"name_description": "gin_trgm_ops"},
        ),
    )

    history_id: str = Field(primary_key=True, max_length=36, description="Unique dataset history row id.")
    table_id: str = Field(foreign_key="table_entity.id", max_length=36, description="Published dataset id that this history version belongs to.")
    table_metadata: dict = Field(default_factory=dict, sa_column=sa.Column(JSONB, nullable=False), description="Archived dataset metadata JSONB for this version.")
    table_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(table_metadata ->> 'tableName')", persisted=True)), description="Generated dataset table name extracted from table_metadata.")
    tenant_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(table_metadata ->> 'tenantName')", persisted=True)), description="Generated tenant name extracted from table_metadata.")
    updatedat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((table_metadata ->> 'updatedAt')::bigint)", persisted=True)), description="Generated updated timestamp extracted from table_metadata.")
    updatedby: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(table_metadata ->> 'updatedBy')", persisted=True)), description="Generated updated-by user id extracted from table_metadata.")
    deleted: Optional[bool] = Field(default=None, sa_column=sa.Column(sa.Boolean(), sa.Computed("((table_metadata ->> 'deleted')::boolean)", persisted=True)), description="Generated soft-delete flag extracted from table_metadata.")
    createdat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((table_metadata ->> 'createdAt')::bigint)", persisted=True)), description="Generated created timestamp extracted from table_metadata.")
    attributes_metadata: Optional[dict] = Field(default=None, sa_column=sa.Column(JSONB, sa.Computed("((table_metadata ->> 'attributesMetadata')::jsonb)", persisted=True)), description="Generated attributes metadata extracted from table_metadata when present.")
    domain_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(table_metadata ->> 'domainId')", persisted=True)), description="Generated domain id extracted from table_metadata.")
    tenant_unique_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(table_metadata ->> 'tenantUniqueId')", persisted=True)), description="Generated tenant unique id extracted from table_metadata.")
    table_metadata_text: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("(table_metadata::text)", persisted=True)), description="Generated text representation of table_metadata for full-text search.")
    name_description: Optional[str] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Text(),
            sa.Computed(
                "('Table Name: ' || COALESCE(table_metadata ->> 'tableName', table_metadata ->> 'tablename', '') || ', Table Description: ' || COALESCE(table_metadata ->> 'tableDescription', table_metadata ->> 'templateDescription', ''))",
                persisted=True,
            ),
        ),
        description="Generated searchable dataset name and description text.",
    )
    table_description: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("""(table_metadata ->> 'Table Description')""", persisted=True)), description="Generated dataset description extracted from table_metadata.")
    version_seq: int = Field(sa_column=sa.Column(sa.Integer(), nullable=False), description="Sequential version number for the dataset record.")
    version_label: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=16), sa.Computed("(version_seq::text || '.0')", persisted=True)), description="Generated version label derived from version_seq.")
    requester_id: Optional[str] = Field(default=None, max_length=32, description="Requester user id associated with the change that created this history version.")
    approver_id: Optional[str] = Field(default=None, max_length=32, description="Checker user id that approved the change that created this history version.")
    requester_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True), description="Timestamp when the requester submitted the change.")
    approver_ts: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True), description="Timestamp when the checker approved the change.")
    dictionary_action: str = Field(sa_column=sa.Column(sa.CHAR(length=1), nullable=False), description="Dictionary action that produced this history version: A add, U update, or D delete.")
    approval_status: str = Field(default="A", sa_column=sa.Column(sa.CHAR(length=1), nullable=False, server_default=sa.text("'A'")), description="Approval status for this history row, normally A after approval.")
    record_status: str = Field(sa_column=sa.Column(sa.CHAR(length=1), nullable=False), description="Record status for this version: A active or D disabled.")
    effective_from: Any = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False), description="Timestamp when this dataset version became effective.")
    effective_to: Any = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False), description="Timestamp when this dataset version stopped being effective.")
    source_request_id: Optional[str] = Field(default=None, foreign_key="approval_request.request_id", max_length=36, description="Approval request id that produced this history version.")
    archived_at: Optional[Any] = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), description="Timestamp when this history row was archived.")
