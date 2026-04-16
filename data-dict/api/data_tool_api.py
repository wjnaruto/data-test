from fastapi import APIRouter, Query

from services.data_tool_impl import DataToolService


service = DataToolService()
router = APIRouter()


@router.get(path="/insert", tags=["Data Tool"], summary="Insert metadata", description="Insert metadata.")
async def insert_data(
        key: str = Query(default=..., description="The key to insert"),
        file_name: str = Query(default=..., description="The file name to insert"),
        template_type: str = Query(default=..., description="The template type to insert")
):
    return await service.insert_data(key, file_name, template_type)


@router.get(path="/extension", tags=["Data Tool"], summary="Install extension", description="Install extension.")
async def install_extension():
    return await service.install_extension()


@router.get(
    path="/delete_attributes_metadata_by_domain",
    tags=["Data Tool"],
    summary="Delete Old Metadatas by domain",
    description="Delete Old Metadatas by domain."
)
async def delete_attributes_metadata_by_domain(domain_name: str = Query(default=..., description="The domain name to delete")):
    return await service.delete_attributes_metadata_by_domainId(domain_name)


@router.get(
    path="/delete_attributes_metadata_by_tenant",
    tags=["Data Tool"],
    summary="Delete Old Metadatas by tenant id",
    description="Delete Old Metadatas by tenant id."
)
async def delete_attributes_metadata_by_tenant(tenant_id: str = Query(default=..., description="The tenant name to delete")):
    return await service.delete_attributes_metadata_by_tenant(tenant_id)


@router.get(path="/insert/glossary", tags=["Data Tool"], summary="Insert glossary", description="Insert glossary.")
async def insert_glossary(
        key: str = Query(default=..., description="The key to insert"),
        file_name: str = Query(default=..., description="The file name to insert")
):
    return await service.insert_glossary(key, file_name)
