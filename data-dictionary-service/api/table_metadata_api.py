from fastapi import APIRouter, Query, HTTPException, Depends

from services.table_metadata_impl import TableMetadataService
from models.models import TableResponseVO
from typing import Optional, Tuple


service = TableMetadataService()
router = APIRouter()


def require_one_of(
    domain_name: Optional[str] = Query(None),
    tenant_name: Optional[str] = Query(None),
) -> Tuple[Optional[str], Optional[str]]:
    if not domain_name and not tenant_name:
        raise HTTPException(
            status_code=400,
            detail="At least one of the parameters 'domain_name' or 'tenant_name' is required.",
        )
    return domain_name, tenant_name


@router.get(
    "/tables",
    response_model=TableResponseVO,
    tags=["Table Metadata"],
    summary="Get Tables Metadata",
    description="Retrieve table entities based on given parameters. Either 'domain_name' or 'tenant_name' must be provided.",
)
async def get_tables(
    page: int = Query(default=1, description="The page number to retrieve"),
    size: int = Query(default=10, description="The number of items per page"),
    table_name: str = Query(default=None, description="The name of the table to search for"),
    deps: Tuple[Optional[str], Optional[str]] = Depends(require_one_of),
):
    domain_name, tenant_name = deps
    return await service.get_tables(page, size, domain_name, tenant_name, table_name)


@router.get(
    "/tables/download",
    tags=["Table Metadata"],
    summary="Download Tables Metadata as Excel",
    description="Download table entities as an Excel file.",
)
async def download_tables_as_excel(
    page: int = Query(default=1, description="The page number to retrieve"),
    size: int = Query(default=10, description="The number of items per page"),
    domain_name: str = Query(
        default=None,
        description="The name of the domain to search for tables (required if tenant_name is not provided)",
    ),
    tenant_name: str = Query(
        default=None,
        description="The name of the tenant to search for tables (required if domain_name is not provided)",
    ),
    table_name: str = Query(default=None, description="The name of the table to search for"),
):
    if not tenant_name and not domain_name:
        raise HTTPException(
            status_code=400,
            detail="At least one of the parameters 'domain_name' or 'tenant_name' must be provided.",
        )

    return await service.generate_excel_for_tables(page, size, domain_name, tenant_name, table_name)
