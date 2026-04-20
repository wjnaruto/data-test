import io
from typing import List

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from core.config import get_logger
from data import attribute_queries
from models.models import AttributeVO, AttributeResponseVO


logger = get_logger(__name__)


class AttributeMetadataService:

    async def get_attributes(self, page, size, table_id) -> List[AttributeVO]:
        try:
            total_count, records = await attribute_queries.get_attributes_by_table_id(page, size, table_id)
            total_count = total_count[0]["count"] if total_count else 0

            if not records:
                return AttributeResponseVO(attributes=[], total=total_count, page=page, pageSize=size)

            result = []
            for record in records:
                attribute_vo = AttributeVO.from_record(record["metadata"])
                result.append(attribute_vo)

            return AttributeResponseVO(attributes=result, total=total_count, page=page, pageSize=size)
        except Exception as ex:
            logger.error("Error fetching Table data: %s", ex)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def generate_excel_for_attributes(self, table_id):
        attribute_response = await self.get_attributes(1, 999, table_id)

        wb = Workbook()
        ws = wb.active
        ws.title = "Attributes Metadata"

        headers = [
            "Tenant Name",
            "Table Name",
            "Physical Table Name",
            "Field Name",
            "Physical Full Name",
            "Field Type",
            "Field Description",
            "Field Description (Short)",
            "Is Primary Key",
            "Field Type 2",
            "Field Type 3",
            "Is Nullable",
            "Field Type 4",
            "Is PII",
            "Is Sensitive",
            "Data Type",
            "List Values",
            "All PII",
            "Vendor Name",
            "Business Area",
            "Source System ID",
            "IT owner ID",
            "Source System ID",
            "Data Classification",
            "Client View",
            "Business Owner ID",
        ]

        ws.append(headers)

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for attribute in attribute_response.attributes:
            ws.append([
                attribute.tenantName,
                attribute.tableName,
                attribute.physicalTableName,
                attribute.fieldName,
                attribute.physicalFullName,
                "",
                attribute.fieldDescription,
                attribute.fieldDescriptionShort,
                attribute.isPrimaryKey,
                "",
                "",
                attribute.nullable,
                "",
                attribute.allPii,
                attribute.isSensitive,
                attribute.dataType,
                attribute.listValues,
                attribute.allPii,
                attribute.vendorName,
                attribute.businessArea,
                attribute.source,
                attribute.itOwnerId if hasattr(attribute, "itOwnerId") else "",
                attribute.source,
                attribute.dataClassification,
                attribute.client,
                attribute.businessOwnerId if hasattr(attribute, "businessOwnerId") else "",
            ])

        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=attributes_metadata.xlsx"},
        )
