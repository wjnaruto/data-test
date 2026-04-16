from fastapi import APIRouter, Query

from services.attribute_metadata_impl import AttributeMetadataService
from models.models import AttributeResponseVO


service = AttributeMetadataService()
router = APIRouter()


@router.get(
    path="/attributes",
    response_model=AttributeResponseVO,
    tags=["Attribute Metadata"],
    summary="Get Attributes Metadata",
    description="Retrieve attribute entities based on given parameters. Either 'domain_name' or 'tenant_name' must be provided."
)
async def get_attributes(
        page: int = Query(default=1, description="The page number to retrieve"),
        size: int = Query(default=10, description="The number of items per page"),
        table_id: str = Query(default=..., description="The id of the table to search for")
):
    return await service.get_attributes(page, size, table_id)


@router.get(
    path="/attributes/download",
    tags=["Attribute Metadata"],
    summary="Download Attribute Metadata as Excel",
    description="Download attribute entities as an Excel file."
)
async def download_tables_as_excel(
        table_id: str = Query(default=None, description="The id of the table to search for")
):
    # Call the service method to generate and return the Excel file
    return await service.generate_excel_for_attributes(table_id)
