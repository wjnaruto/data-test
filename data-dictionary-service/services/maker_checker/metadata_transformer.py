from __future__ import annotations

from typing import Any, Dict

from schemas.maker_checker.submit import AttributeMetadataInput, DatasetMetadataInput


def _set_if_not_none(target: Dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = value


def dataset_input_to_table_metadata(input_data: DatasetMetadataInput) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    _set_if_not_none(result, "Domain Name", input_data.domainName)
    _set_if_not_none(result, "tableName", input_data.tableName)
    _set_if_not_none(result, "Table Name", input_data.tableName)
    _set_if_not_none(result, "Physical Table Name", input_data.physicalTableName)
    _set_if_not_none(result, "Table Description", input_data.tableDescription)
    _set_if_not_none(result, "Country of Origin", input_data.countryOfOrigin)
    _set_if_not_none(result, "Data Localisation", input_data.dataLocalisation)
    _set_if_not_none(result, "Update Frequency", input_data.updateFrequency)
    _set_if_not_none(result, "Data Classification", input_data.dataClassification)
    _set_if_not_none(result, "Client view", input_data.clientView)
    _set_if_not_none(result, "Client View", input_data.clientView)
    _set_if_not_none(result, "Business Owner ID", input_data.businessOwnerId)
    _set_if_not_none(result, "IT owner ID", input_data.itOwnerId)
    _set_if_not_none(result, "domainId", input_data.domainId)
    _set_if_not_none(result, "tenantUniqueId", input_data.tenantUniqueId)
    _set_if_not_none(result, "tenantId", input_data.tenantId)
    _set_if_not_none(result, "tenantName", input_data.tenantName)

    return result


def attribute_input_to_metadata(input_data: AttributeMetadataInput) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    _set_if_not_none(result, "Tenant Name", input_data.tenantName)
    _set_if_not_none(result, "tenantName", input_data.tenantName)
    _set_if_not_none(result, "Table Name", input_data.tableName)
    _set_if_not_none(result, "Physical Table Name", input_data.physicalTableName)
    _set_if_not_none(result, "Field Name", input_data.fieldName)
    _set_if_not_none(result, "Physical Field Name", input_data.physicalFieldName)
    _set_if_not_none(result, "Field Description (Long)", input_data.fieldDescriptionLong)
    _set_if_not_none(result, "Field Description", input_data.fieldDescriptionLong)
    _set_if_not_none(result, "Field Description (Short)", input_data.fieldDescriptionShort)
    _set_if_not_none(result, "Is Primary Key", input_data.isPrimaryKey)
    _set_if_not_none(result, "Field Type", input_data.fieldType)
    _set_if_not_none(result, "Data Type", input_data.dataType)
    _set_if_not_none(result, "Is List", input_data.isList)
    _set_if_not_none(result, "List Values", input_data.listValues)
    _set_if_not_none(result, "Is PII", input_data.isPii)
    _set_if_not_none(result, "Is Vendor Data", input_data.isVendorData)
    _set_if_not_none(result, "Vendor Name", input_data.vendorName)
    _set_if_not_none(result, "Is HSBC BDE", input_data.isHsbcBde)
    _set_if_not_none(result, "HSBC Attribute ID", input_data.hSBCAttributeId)
    _set_if_not_none(result, "Data Classification", input_data.dataClassification)
    _set_if_not_none(result, "Client view", input_data.clientView)
    _set_if_not_none(result, "Client View", input_data.clientView)
    _set_if_not_none(result, "Business Owner ID", input_data.businessOwnerId)
    _set_if_not_none(result, "IT owner ID", input_data.itOwnerId)
    _set_if_not_none(result, "domainId", input_data.domainId)
    _set_if_not_none(result, "tenantUniqueId", input_data.tenantUniqueId)
    _set_if_not_none(result, "tenantId", input_data.tenantId)
    _set_if_not_none(result, "tableId", input_data.tableId)

    return result
