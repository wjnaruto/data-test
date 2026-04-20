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

    history_id: str = Field(primary_key=True, max_length=36)
    table_id: str = Field(foreign_key="table_entity.id", max_length=36)
    table_metadata: dict = Field(default_factory=dict, sa_column=sa.Column(JSONB, nullable=False))
    table_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(table_metadata ->> 'tableName')", persisted=True)))
    tenant_name: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(table_metadata ->> 'tenantName')", persisted=True)))
    updatedat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((table_metadata ->> 'updatedAt')::bigint)", persisted=True)))
    updatedby: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=256), sa.Computed("(table_metadata ->> 'updatedBy')", persisted=True)))
    deleted: Optional[bool] = Field(default=None, sa_column=sa.Column(sa.Boolean(), sa.Computed("((table_metadata ->> 'deleted')::boolean)", persisted=True)))
    createdat: Optional[int] = Field(default=None, sa_column=sa.Column(sa.BigInteger(), sa.Computed("((table_metadata ->> 'createdAt')::bigint)", persisted=True)))
    attributes_metadata: Optional[dict] = Field(default=None, sa_column=sa.Column(JSONB, sa.Computed("((table_metadata ->> 'attributesMetadata')::jsonb)", persisted=True)))
    domain_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(table_metadata ->> 'domainId')", persisted=True)))
    tenant_unique_id: Optional[str] = Field(default=None, sa_column=sa.Column(sa.String(length=36), sa.Computed("(table_metadata ->> 'tenantUniqueId')", persisted=True)))
    table_metadata_text: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text(), sa.Computed("(table_metadata::text)", persisted=True)))
    name_description: Optional[str] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Text(),
            sa.Computed(
                "('Table Name: ' || COALESCE(table_metadata ->> 'tableName', table_metadata ->> 'tablename', '') || ', Table Description: ' || COALESCE(table_metadata ->> 'tableDescription', table_metadata ->> 'templateDescription', ''))",
                persisted=True,
            ),
        ),
    )
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

