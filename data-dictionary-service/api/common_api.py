from fastapi import APIRouter, Query

from services.data_dictionary_impl import DataDictionaryService


service = DataDictionaryService()
router = APIRouter()


@router.get(
    path="/search",
    tags=["Search Metadata"],
    summary="Search data dictionary",
    description="Wildcard search for data dictionary."
)
async def search_data_dictionary(
        text: str = Query(default=..., description="Search text"),
        domain_name: str = Query(default=None, description="The name of the domain to search for"),
        tenant_name: str = Query(default=None, description="The name of the tenant to search for"),
        page: int = Query(default=1, description="The page number to retrieve"),
        size: int = Query(default=10, description="The number of items per page")
):
    return await service.search_data_dictionary(page, size, text, domain_name, tenant_name)


@router.get(
    path="/download/template",
    tags=["Template"],
    summary="Download Template",
    description="Download the template file for data dictionary."
)
async def download_template():
    return await service.download_template()
