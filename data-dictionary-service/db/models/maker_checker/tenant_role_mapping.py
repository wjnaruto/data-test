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
        description="Generated primary key for the tenant role mapping.",
    )
    domain_id: str = Field(foreign_key="domain_entity.id", max_length=36, description="Domain id associated with this tenant role mapping.")
    tenant_unique_id: str = Field(foreign_key="tenant_entity.id", max_length=36, description="Tenant unique id protected by this role mapping.")
    role_type: str = Field(max_length=20, description="Data Dictionary role type mapped from the AD group: REQUESTER, APPROVER, or VIEWER.")
    ad_group_name: str = Field(max_length=256, description="AD group or authority name returned by the auth server.")
    is_active: bool = Field(
        default=True,
        sa_column=sa.Column(sa.Boolean(), nullable=False, server_default=sa.text("true")),
        description="Whether this role mapping is active and should be used for authorization.",
    )
    created_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        description="Timestamp when the role mapping was created.",
    )
    updated_at: Optional[Any] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        description="Timestamp when the role mapping was last updated.",
    )
