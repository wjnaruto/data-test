from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field


class DomainVO(BaseModel):
    id: str = Field("", description="The unique identifier of the domain")
    name: str = Field("", description="The name of the domain")
    fqnhash: Optional[str] = Field("", description="The fully qualified name hash of the domain")
    updatedAt: int = Field(None, description="The timestamp when the domain was last updated")
    updatedBy: str = Field("", description="The user who last updated the domain")
    createdAt: int = Field(None, description="The timestamp when the domain was created")

    @classmethod
    def from_record(cls, metadata):
        return cls(**metadata)


class TenantVO(BaseModel):
    id: str = Field(..., description="The unique identifier of the tenant")
    tenantName: str = Field("", description="Tenant Name - The name of the tenant")
    updatedAt: int = Field(None, description="The timestamp when the tenant was last updated")
    updatedBy: str = Field("", description="The user who last updated the tenant")
    createdAt: int = Field(None, description="The timestamp when the tenant was created")
    domainId: str = Field("", description="The unique identifier of the domain associated with the tenant")
    domainName: str = Field("", description="The name of the domain associated with the tenant")
    tenantId: str = Field("", description="Tenant ID - The unique identifier of the tenant in the Mesh")
    tenantStatus: str = Field("", description="Tenant Status - The status of the tenant")
    tenantDescription: str = Field("", description="Tenant Description - The description of the tenant")
    tenantOtherInformation: str = Field(
        "",
        description="Tenant Other Information - other information about the tenant",
    )
    tenantSupportContactDetails: str = Field(
        "",
        description="Tenant Support Contact Details - The contact details for tenant support",
    )
    sourceSystemsName: str = Field("", description="Source System Name(s) - The name of the source systems")
    sourceSystemEIMId: str = Field("", description="Source System EIM ID(s) - The EIM ID(s) of the source systems")
    dataVisaId: str = Field("", description="DataVisa ID(s) - The visuals of the tenant")
    productionLocations: str = Field("", description="Production Locations - The production locations of the tenant")
    productionDataVolumes: str = Field(
        "",
        description="Production Data Volumes - The production data volumes of the tenant",
    )
    consumers: str = Field("", description="Consumers - The consumers of the tenant")
    dataSetsOrTables: str = Field(
        "",
        description="Data Sets / Tables - The data sets or tables of the tenant",
    )
    dssID: str = Field("", description="DSS ID(s) - The DSS ID of the tenant")
    datasets: List[Dict[str, Any]] = Field(default_factory=list, description="Datasets of the tenant")
    area: str = Field("", description="Area - The area of the tenant")

    @classmethod
    def from_record(cls, tenant_metadata, domain_metadata):
        return cls(
            **tenant_metadata,
            domainName=domain_metadata.get("name", "") if domain_metadata else "",
            tenantName=tenant_metadata.get("Tenant Name", tenant_metadata.get("tenant_name", "")),
            tenantId=tenant_metadata.get("Tenant ID", ""),
            dataVisaId=tenant_metadata.get("DataVisa ID(s)", ""),
            tenantStatus=tenant_metadata.get("Tenant Status", ""),
            sourceSystemsName=tenant_metadata.get("Source System Name(s)", ""),
            tenantDescription=tenant_metadata.get("Tenant Description", ""),
            sourceSystemEIMId=tenant_metadata.get("Source System EIM ID(s)", ""),
            tenantOtherInformation=tenant_metadata.get("Tenant Other Information", ""),
            tenantSupportContactDetails=tenant_metadata.get("Tenant Support Contact Details", ""),
            dataSetsOrTables=tenant_metadata.get("Data Sets / Tables", ""),
            dssID=tenant_metadata.get("DSS ID(s)", ""),
            consumers=tenant_metadata.get("Consumers", ""),
            productionLocations=tenant_metadata.get("Production Locations", ""),
            productionDataVolumes=tenant_metadata.get("Production Data Volumes", ""),
            area=tenant_metadata.get("Area", ""),
        )


class TableVO(BaseModel):
    id: str = Field(..., description="The unique identifier of the table")
    tableName: str = Field(..., description="Table Name - The fully qualified name of the table")
    domainId: str = Field(..., description="The unique identifier of the domain associated with the table")
    domainName: Optional[str] = Field("", description="Domain Name - The name of the domain associated with the table")
    tenantUniqueId: str = Field("", description="The unique identifier of the tenant associated with the table")
    tenantId: str = Field("", description="Tenant ID - The unique identifier of the tenant in the Mesh")
    tenantName: Optional[str] = Field("", description="The name of the tenant associated with the table")
    physicalTableName: str = Field("", description="The physical name of the table")
    tableDescription: str = Field("", description="The description of the table")
    countryOfOrigin: str = Field("", description="The country of origin of the table")
    dataLocalisation: str = Field("", description="The data localisation of the table")
    updateFrequency: str = Field("", description="The update frequency of the table")
    dataClassification: str = Field("", description="The data classification of the table")
    clientView: str = Field("", description="The client view of the table")
    businessOwnerId: str = Field("", description="The business owner ID of the table")
    itOwnerId: str = Field("", description="IT owner ID of the table")
    attributeMetadata: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Metadata of the table's attributes",
    )
    updatedAt: int = Field(None, description="The timestamp when the table was last updated")
    updatedBy: str = Field("", description="The user who last updated the table")
    deleted: Optional[bool] = Field(None, description="Indicates if the table is deleted")
    createdAt: int = Field(None, description="The timestamp when the table was created")
    attributes: List[Dict[str, Any]] = Field(default_factory=list, description="Attributes of the table")

    @classmethod
    def from_record(cls, metadata):
        return cls(
            id=metadata.get("id", ""),
            tableName=metadata.get("tableName", ""),
            domainId=metadata.get("domainId", ""),
            domainName=metadata.get("Domain Name", metadata.get("Product", "")),
            tenantUniqueId=metadata.get("tenantUniqueId", ""),
            tenantId=metadata.get("tenantId", ""),
            tenantName=metadata.get("tenantName", ""),
            attributeMetadata=sorted(
                metadata.get("attributesMetadata", metadata.get("field_list", [])),
                key=lambda x: (x.get("Is Primary Key", "").lower() != "yes", x.get("Field Name", "").lower()),
            ),
            physicalTableName=metadata.get("Physical Table Name", ""),
            tableDescription=metadata.get("Table Description", metadata.get("Template Description", "")),
            countryOfOrigin=metadata.get("Country of Origin", ""),
            dataLocalisation=metadata.get("Data Localisation", ""),
            updateFrequency=metadata.get("Update Frequency", ""),
            dataClassification=metadata.get("Data Classification", ""),
            clientView=str(metadata.get("Client view", "")),
            businessOwnerId=str(metadata.get("Business Owner ID", "")),
            itOwnerId=str(metadata.get("IT owner ID", "")),
            updatedAt=metadata.get("updatedAt", ""),
            updatedBy=metadata.get("updatedBy", ""),
            deleted=metadata.get("deleted", None),
            createdAt=metadata.get("createdAt", ""),
            attributes=metadata.get("attributes", []),
        )


class TableResponseVO(BaseModel):
    tables: List[TableVO] = Field(default_factory=list, description="List of tables")
    total: int = Field(None, description="Total number of tables")
    page: int = Field(None, description="Page number")
    pageSize: int = Field(None, description="Page size")


class AttributeVO(BaseModel):
    id: str = Field(..., description="The unique identifier of the attribute")
    fieldName: str = Field(..., description="Field Name of the attribute")
    domainId: str = Field("", description="Domain ID that the attribute belongs to")
    domainName: str = Field("", description="Domain Name that the attribute belongs to")
    tenantUniqueId: str = Field("", description="The unique identifier of the tenant that the attribute belongs to")
    tenantId: str = Field("", description="Tenant ID that the attribute belongs to")
    tenantName: str = Field("", description="Tenant Name that the attribute belongs to")
    tableId: str = Field("", description="Table ID that the attribute belongs to")
    tableName: str = Field("", description="Table Name that the attribute belongs to")
    physicalTableName: str = Field("", description="The physical table name as stored in the database")
    physicalFieldName: str = Field("", description="The physical name of the field in the database")
    fieldDescriptionLong: str = Field("", description="Long description of the field")
    fieldDescriptionShort: str = Field("", description="Short description of the field")
    isPrimaryKey: str = Field("", description="Indicates if the field is a primary key")
    fieldType: str = Field("", description="The type of the field")
    dataType: str = Field("", description="The type of the field")
    isList: str = Field("", description="Indicates if the field is a list")
    listValues: str = Field("", description="List values of the field if it is a list")
    isPii: str = Field("", description="Indicates if the field is PII")
    isVendorData: str = Field("", description="Indicates if the field is vendor data")
    vendorName: str = Field("", description="Name of the vendor")
    isHsbcBde: str = Field("", description="Indicates if the field is an HSBC BDE")
    HSBCAttributeId: str = Field("", description="The unique identifier of the attribute in HSBC")
    dataClassification: str = Field("", description="Data classification of the field")
    clientView: str = Field("", description="Client view of the field")
    businessOwnerId: str = Field("", description="Business owner ID of the field")
    itOwnerId: str = Field("", description="IT owner ID of the field")
    deleted: Optional[bool] = Field(None, description="Indicates if the attribute is deleted")
    createdAt: int = Field(None, description="The timestamp when the attribute was created")
    updatedAt: int = Field(None, description="The timestamp when the attribute was last updated")
    updatedBy: str = Field("", description="The user who last updated the attribute")

    @classmethod
    def from_record(cls, metadata):
        return cls(
            **metadata,
            fieldName=metadata.get("Field Name", ""),
            domainName=metadata.get("Domain Name", metadata.get("Product", "")),
            tenantName=metadata.get("tenantName", metadata.get("Tenant Name", "")),
            tableName=metadata.get("Table Name", ""),
            physicalTableName=metadata.get("Physical Table Name", ""),
            physicalFieldName=metadata.get("Physical Field Name", ""),
            fieldDescriptionLong=metadata.get("Field Description (Long)", metadata.get("Field Description", "")),
            fieldDescriptionShort=metadata.get("Field Description (Short)", ""),
            isPrimaryKey=metadata.get("Is Primary Key", ""),
            fieldType=metadata.get("Field Type", ""),
            dataType=metadata.get("Data Type", ""),
            isList=metadata.get("Is List", ""),
            listValues=metadata.get("List Values", ""),
            isPii=metadata.get("Is PII", ""),
            isVendorData=metadata.get("Is Vendor Data", ""),
            vendorName=metadata.get("Vendor Name", ""),
            isHsbcBde=metadata.get("Is HSBC BDE", ""),
            HSBCAttributeId=metadata.get("HSBC Attribute ID", ""),
            dataClassification=metadata.get("Data Classification", ""),
            clientView=str(metadata.get("Client view", "")),
            businessOwnerId=str(metadata.get("Business Owner ID", "")),
            itOwnerId=str(metadata.get("IT owner ID", "")),
            deleted=metadata.get("deleted", None),
            createdAt=metadata.get("createdAt", None),
            updatedAt=metadata.get("updatedAt", None),
            updatedBy=metadata.get("updatedBy", ""),
        )


class AttributeResponseVO(BaseModel):
    attributes: List[AttributeVO] = Field(default_factory=list, description="List of attributes")
    total: int = Field(None, description="Total number of attributes")
    page: int = Field(None, description="Page number")
    pageSize: int = Field(None, description="Page size")


class DataDictionarySearchVo(BaseModel):
    domain: DomainVO = Field(None, description="The domain entity")
    tenant: TenantVO = Field(None, description="The tenant entity")


class DatasetVO(BaseModel):
    tableName: str
    tableDescription: str
    attributes: List[AttributeVO]


class TenantDatasetVO(BaseModel):
    tenantName: str
    domainName: str
    datasets: List[Any]


class SearchResultVO(BaseModel):
    data: List[Any]
    total: int
    page: int
    pageSize: int
