from fastapi import APIRouter, Query

from services.glossary_impl import GlossaryService
from models.glossary import GlossaryResponseVO
from typing import List


service = GlossaryService()
router = APIRouter()


@router.get(
    "/glossary",
    tags=["Glossary"],
    summary="Glossary",
    description="Search glossary by key. The key is a wildcard search text.",
)
async def glossary_by_key(
    page: int = Query(default=1, description="The page number to retrieve"),
    size: int = Query(default=1000, description="The number of items per page"),
    glossary_key: List[str] = Query(
        default=...,
        description="Search text, Concatenate with semicolon, e.g. 'key1;key2;key3...'",
    ),
    rollup: int = Query(
        default=0,
        description="Rollup lever, e.g. 0 = field lever, 1 = template lever, 2 = product domain lever, etc.",
    ),
):
    return await service.glossary_by_key(page, size, glossary_key, rollup)
