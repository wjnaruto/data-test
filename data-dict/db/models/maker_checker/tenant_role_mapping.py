from __future__ import annotations

from .common import Any, Field, Optional, SQLModel, sa


class TenantRoleMapping(SQLModel, table=True):
    __tablename__ = "tenant_role_mapping"
    __table_args__ = (
        sa.CheckConstraint(
            "role_type IN ('REQUESTER', 'APPROVER', 'VIEWER')",
            name="tenant_role_mapping_role_type_chk",
        ),
        sa.UniqueConstraint("tenant_unique_id", "role_type", name="tenant_role_mapping_uq"),
        sa.Index("tenant_role_mapping_active_idx", "tenant_unique_id", "role_type", "is_active"),
    )

    mapping_id: Optional[int] = Field(
        default=None,
        sa_column=sa.Column(sa.BigInteger(), sa.Identity(always=True), primary_key=True, nullable=False),
    )
    domain_id: str = Field(foreign_key="domain_entity.id", max_length=36)
    tenant_unique_id: str = Field(foreign_key="tenant_entity.id", max_length=36)
    role_type: str = Field(max_length=20)
    ad_group_name: str = Field(max_length=256)
    is_active: bool = Field(
        default=True,
        sa_column=sa.Column(sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    created_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    updated_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

