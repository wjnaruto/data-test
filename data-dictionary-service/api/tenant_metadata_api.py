from typing import List

from fastapi import APIRouter, Query, HTTPException

from services.tenant_metadata_impl import TenantMetadataService
from models.models import TenantVO


service = TenantMetadataService()
router = APIRouter()


@router.get(
    "/tenants",
    response_model=List[TenantVO],
    tags=["Tenant Metadata"],
    summary="Get Tenants Metadata",
    description="Search tenant metadata by tenant name or domain name. Either 'domain_name' or 'tenant_name' must be provided.",
)
async def get_tenants(
    domain_name: str = Query(
        default=None,
        description="The name of the domain to search for tenants (required if tenant_name is not provided)",
    ),
    tenant_name: str = Query(
        default=None,
        description="The name of the tenant to search for (required if domain_name is not provided)",
    ),
):
    if not tenant_name and not domain_name:
        raise HTTPException(
            status_code=400,
            detail="At least one of the parameters 'tenant_name' or 'domain_name' must be provided.",
        )
    return await service.get_tenants(tenant_name, domain_name)


@router.get(
    "/tenants/names",
    response_model=List[str],
    tags=["Tenant Metadata"],
    summary="Get All Tenant Names",
    description="Retrieve all tenant names.",
)
async def get_all_tenant_names():
    return await service.get_all_tenants_names()
