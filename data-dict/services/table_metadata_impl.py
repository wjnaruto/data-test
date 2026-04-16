import json as json_lib
from io import BytesIO
from typing import List

import openpyxl
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from openpyxl.styles import Font

from core.config import get_logger
from db.queries import table_queries
from models.models import TableVO, TableResponseVO


logger = get_logger(__name__)


class TableMetadataService:

    async def get_tables(self, page, size, domain_name, tenant_name, table_name) -> List[TableVO]:
        try:
            total_count, records = await table_queries.get_tables(page, size, domain_name, tenant_name, table_name)
            total_count = total_count[0]['count']
            if not records:
                return TableResponseVO(tables=[], total=total_count, page=page, pageSize=size)
            result = []
            for record in records:
                domain_name = json_lib.loads(record['domain_json']).get('name')
                table_vo = TableVO.from_record(json_lib.loads(record['table_json'])).copy(update={"domainName": domain_name})
                result.append(table_vo)
            return TableResponseVO(tables=result, total=total_count, page=page, pageSize=size)
        except Exception as e:
            logger.error(f"Error fetching Table data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def generate_excel_for_tables(self, page, size, domain_name, tenant_name, table_name):
        # Fetch table data
        table_response = await self.get_tables(page, size, domain_name, tenant_name, table_name)

        # Create an Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Tables Metadata"

        # Add headers
        headers = [
            "Domain Name",
            "Tenant Name",
            "Table Name",
            "Physical Table Name",
            "Table Description",
            "Country of Origin",
            "Data Localisation",
            "Update Frequency",
            "Data Classification",
            "Client View",
            "Business Owner ID",
            "IT Owner ID"
        ]
        ws.append(headers)

        # Make headers bold
        for cell in ws[1]:  # First row contains the headers
            cell.font = Font(bold=True)

        # Add data rows
        for table in table_response.tables:
            ws.append([
                table.domainName,
                table.tenantName,
                table.tableName,
                table.physicalTableName,  # Assuming this field exists in the TableVO model
                table.tableDescription,  # Assuming this field exists in the TableVO model
                table.countryOfOrigin,  # Assuming this field exists in the TableVO model
                table.dataLocalisation,  # Assuming this field exists in the TableVO model
                table.updateFrequency,  # Assuming this field exists in the TableVO model
                table.dataClassification,  # Assuming this field exists in the TableVO model
                table.clientView,  # Assuming this field exists in the TableVO model
                table.businessOwnerId,  # Assuming this field exists in the TableVO model
                table.itOwnerId  # Assuming this field exists in the TableVO model
            ])

        # Save workbook to a BytesIO stream
        file_stream = BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        # Return the Excel file as a response
        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=tables_metadata.xlsx"}
        )
