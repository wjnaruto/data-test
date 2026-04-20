from fastapi import APIRouter, Query
from typing import List

from services.data_dictionary_impl import DataDictionaryService
from models.models import DomainVO


service = DataDictionaryService()
router = APIRouter()


@router.get(
    path="/domain",
    response_model=DomainVO,
    tags=["Domain Metadata"],
    summary="Get Domain Metadata",
    description="Retrieve a domain entity by its name."
)
async def get_domain(name: str = Query(default=..., description="The name of the domain to retrieve")):
    return await service.get_domain(name)


@router.get(
    path="/domain/names",
    response_model=List[str],
    tags=["Domain Metadata"],
    summary="Get All Domain names",
    description="Retrieve all domain names."
)
async def get_all_domain_names():
    return await service.get_all_domain_names()
