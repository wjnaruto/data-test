import json as json_lib
import io
from fastapi.responses import StreamingResponse
from fastapi import HTTPException
from google.cloud import storage
from core.config import get_logger
from db.queries import domain_queries
from db.queries import tenant_queries
from db.queries import table_queries
from db.queries import attribute_queries
from core.config import settings
from models.models import DomainVO, TenantVO, TableVO, AttributeVO, TenantDatasetVO, DatasetVO, \
    SearchResultVO


logger = get_logger(__name__)


class DataDictionaryService:
    async def get_domain(self, name: str) -> DomainVO:
        try:
            record = await domain_queries.get_domain(name)
            if not record:
                return DomainVO()
            return DomainVO.from_record(json_lib.loads(record['domain_metadata']))
        except Exception as e:
            logger.error(f"Error fetching Domain data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def search_data_dictionary(self, page, size, text, domain_name, tenant_name):
        try:
            text = f"({'|'.join(text.split())})"
            domainId = ''
            if domain_name:
                domain_metadata = await domain_queries.get_domain(domain_name)
                domain = json_lib.loads(domain_metadata['domain_metadata'])
                domainId = domain.get('id')

            attributes_total_count, attribute_record = await attribute_queries.search_attribute_data_dictionary(page, size, text, tenant_name, domainId)
            if attribute_record:
                attributes_total_count = attributes_total_count[0]['count']
                attribute_result = self._process_attribute_records(attribute_record)
                formatted_result = self._format_attribute_result(attribute_result)
                return SearchResultVO(data=formatted_result, total=attributes_total_count, page=page, pageSize=size)

            table_total_count, table_record = await table_queries.search_table_data_dictionary(page, size, text, tenant_name, domainId)
            if table_record:
                table_total_count = table_total_count[0]['count']
                table_result = self._process_table_records(table_record)
                formatted_result = self._format_table_result(table_result)
                return SearchResultVO(data=formatted_result, total=table_total_count, page=page, pageSize=size)

            tenant_record = await tenant_queries.search_tenant_data_dictionary(text, tenant_name, domainId)

            tenant_result = [TenantVO.from_record(json_lib.loads(record['metadata']), domain_metadata=None)
                                .copy(update={"domainName": record.get('name')}) for record in tenant_record]
            return SearchResultVO(data=tenant_result, total=len(tenant_result), page=page, pageSize=size)
        except Exception as e:
            logger.error(f"Error fetching search data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def _process_attribute_records(self, records):
        attribute_result = {}
        for record in records:
            print(record)
            metadata = json_lib.loads(record['metadata'])
            domain_name = record.get('name')
            attribute_vo = AttributeVO.from_record(metadata)
            # tenant_name = f"{attribute_vo.tenantName} - {attribute_vo.tenantId}"
            tenant_name = f"{domain_name} - {attribute_vo.tenantName}"
            table_name = attribute_vo.tableName
            table_description = metadata.get('Table Description', '')
            if tenant_name not in attribute_result:
                attribute_result[tenant_name] = {}
            if table_name not in attribute_result[tenant_name]:
                attribute_result[tenant_name][table_name] = {"tableDescription": table_description, "attributes": []}
            attribute_result[tenant_name][table_name]["attributes"].append(attribute_vo)
        return attribute_result

    def _format_attribute_result(self, attribute_result):
        return [
            TenantDatasetVO(
                tenantName=tenant_name,
                domainName=tenant_name.split('-')[0].strip(),
                datasets=[
                    DatasetVO(
                        tableName=table_name,
                        tableDescription=table_info["tableDescription"],
                        attributes=table_info["attributes"]
                    )
                    for table_name, table_info in tables.items()
                ]
            )
            for tenant_name, tables in attribute_result.items()
        ]

    def _process_table_records(self, records):
        table_result = {}
        for record in records:
            metadata = json_lib.loads(record['table_metadata'])
            table_vo = TableVO.from_record(metadata)
            domain_name = record.get('name')
            tenant_name = f"{domain_name} - {table_vo.tenantName}"
            table_name = table_vo.tableName
            if tenant_name not in table_result:
                table_result[tenant_name] = {}
            if table_name not in table_result[tenant_name]:
                table_result[tenant_name][table_name] = []
            table_result[tenant_name][table_name].append(table_vo)
        return table_result

    def _format_table_result(self, table_result):
        return [
            TenantDatasetVO(
                tenantName=tenant_name,
                domainName=tenant_name.split('-')[0].strip(),
                datasets=[table[0] for table in tables.values()]
            )
            for tenant_name, tables in table_result.items()
        ]

    async def get_all_domain_names(self):
        try:
            records = await domain_queries.get_all_domain_names()
            domain_names = [
                record['name']
                for record in records
            ]
            return domain_names
        except Exception as e:
            logger.error(f"Error fetching Domain data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def download_template(self):
        try:
            logger.info("Start downloading the template file")
            client = storage.Client(project=settings.project_id)
            bucket_name = f"{settings.project_id}-data-dictionary"
            file_key = f"data/template/Data_Mesh_Dictionary_Template.xlsx"

            bucket = client.bucket(bucket_name)
            blob = bucket.blob(file_key)
            file_bytes = blob.download_as_bytes()

            if not file_bytes:
                raise HTTPException(status_code=404, detail="Template file not found")

            logger.info("End downloading the data file")
            return StreamingResponse(
                io.BytesIO(file_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=Data_Mesh_Dictionary_Template.xlsx"}
            )
        except Exception as e:
            logger.error(f"Error downloading template: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to download template: {e}")
