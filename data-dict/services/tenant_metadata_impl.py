import json as json_lib
from typing import List

from fastapi import HTTPException

from core.config import get_logger
from db.queries import data_access
from models.models import TenantVO
from db.queries import tenant_queries


logger = get_logger(__name__)


class TenantMetadataService:

    async def get_tenants(self, tenant_name: str, domain_name: str) -> List[TenantVO]:
        try:
            records = await tenant_queries.get_tenants(tenant_name, domain_name)
            if not records:
                return []
            result = [
                TenantVO.from_record(
                    json_lib.loads(record['tenant_metadata']),
                    json_lib.loads(record['domain_metadata'])
                )
                for record in records
            ]
            return result
        except Exception as e:
            logger.error(f"Error fetching Tenant data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_all_tenants_names(self):
        try:
            records = await tenant_queries.get_all_tenants_names()
            tenant_names = [
                record['name']
                for record in records
            ]
            return tenant_names
        except Exception as e:
            logger.error(f"Error fetching Tenant data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
