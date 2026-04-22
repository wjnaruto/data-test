from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


DictionaryAction = Literal["A", "U", "D"]
SourceType = Literal["UI"]


class DatasetMetadataInput(BaseModel):
    domainName: Optional[str] = None
    tableName: Optional[str] = None
    physicalTableName: Optional[str] = None
    tableDescription: Optional[str] = None
    countryOfOrigin: Optional[str] = None
    dataLocalisation: Optional[str] = None
    updateFrequency: Optional[str] = None
    dataClassification: Optional[str] = None
    clientView: Optional[str] = None
    businessOwnerId: Optional[str] = None
    itOwnerId: Optional[str] = None
    domainId: Optional[str] = None
    tenantUniqueId: Optional[str] = None
    tenantId: Optional[str] = None
    tenantName: Optional[str] = None


class AttributeMetadataInput(BaseModel):
    tenantName: Optional[str] = None
    tableName: Optional[str] = None
    physicalTableName: Optional[str] = None
    fieldName: Optional[str] = None
    physicalFieldName: Optional[str] = None
    fieldDescriptionLong: Optional[str] = None
    fieldDescriptionShort: Optional[str] = None
    isPrimaryKey: Optional[str] = None
    fieldType: Optional[str] = None
    dataType: Optional[str] = None
    isList: Optional[str] = None
    listValues: Optional[str] = None
    isPii: Optional[str] = None
    isVendorData: Optional[str] = None
    vendorName: Optional[str] = None
    isHsbcBde: Optional[str] = None
    hSBCAttributeId: Optional[str] = None
    dataClassification: Optional[str] = None
    clientView: Optional[str] = None
    businessOwnerId: Optional[str] = None
    itOwnerId: Optional[str] = None
    domainId: Optional[str] = None
    tenantUniqueId: Optional[str] = None
    tenantId: Optional[str] = None
    tableId: Optional[str] = None


class DatasetSubmitItem(BaseModel):
    clientRef: Optional[str] = Field(default=None, description="Client-side temporary ref for new dataset items")
    action: DictionaryAction = Field(..., description="Dataset action: A/U/D")
    entityId: Optional[str] = Field(default=None, description="Current dataset id. Required for U/D")
    tableMetadata: DatasetMetadataInput = Field(default_factory=DatasetMetadataInput, description="Dataset payload")
    currentVersionSeq: Optional[int] = Field(default=None, description="Current version for optimistic checks")

    @model_validator(mode="after")
    def validate_entity_id(self):
        if self.action in {"U", "D"} and not self.entityId:
            raise ValueError("entityId is required for dataset update/delete")
        return self


class AttributeSubmitItem(BaseModel):
    datasetClientRef: Optional[str] = Field(default=None, description="Client-side ref to a new dataset in the same submit")
    action: DictionaryAction = Field(..., description="Attribute action: A/U/D")
    entityId: Optional[str] = Field(default=None, description="Current attribute id. Required for U/D")
    metadata: AttributeMetadataInput = Field(default_factory=AttributeMetadataInput, description="Attribute payload")
    currentVersionSeq: Optional[int] = Field(default=None, description="Current version for optimistic checks")

    @model_validator(mode="after")
    def validate_entity_id(self):
        if self.action in {"U", "D"} and not self.entityId:
            raise ValueError("entityId is required for attribute update/delete")
        return self


class SubmitRequest(BaseModel):
    sourceType: SourceType = Field(default="UI", description="Source type for submit API")
    domainId: str = Field(..., description="Target domain id")
    tenantUniqueId: str = Field(..., description="Target tenant unique id")
    makerComment: Optional[str] = Field(default=None, description="Maker request-level comment")
    dataset: Optional[DatasetSubmitItem] = Field(default=None, description="Deprecated single dataset field for backward compatibility")
    datasets: List[DatasetSubmitItem] = Field(default_factory=list, description="Dataset-level changes in this submit")
    attributes: List[AttributeSubmitItem] = Field(default_factory=list, description="Attribute-level changes from current page")

    @model_validator(mode="before")
    def normalize_datasets(cls, values):
        if not isinstance(values, dict):
            return values

        dataset = values.get("dataset")
        datasets = values.get("datasets")

        if dataset is not None and datasets:
            raise ValueError("Use either dataset or datasets, not both")

        if dataset is not None:
            values["datasets"] = [dataset]
        elif datasets is None:
            values["datasets"] = []

        return values

    @model_validator(mode="after")
    def validate_non_empty(self):
        if not self.datasets and not self.attributes:
            raise ValueError("At least one dataset or attribute change is required")
        return self


class SubmitConflictItem(BaseModel):
    entityType: Literal["DATASET", "ATTRIBUTE"] = Field(..., description="Conflict entity type")
    action: DictionaryAction = Field(..., description="Requested action")
    entityId: Optional[str] = Field(default=None, description="Current entity id if applicable")
    businessKey: str = Field(..., description="Business key used for conflict detection")
    existingRequestId: str = Field(..., description="Existing pending request id")
    message: str = Field(..., description="Conflict description")


class SubmitResponse(BaseModel):
    requestId: str = Field(..., description="Created approval request id")
    requestStatus: str = Field(..., description="Request status after submit")
    totalItems: int = Field(..., description="Total number of staged items")
    datasetItems: int = Field(..., description="Number of staged dataset items")
    attributeItems: int = Field(..., description="Number of staged attribute items")
    message: str = Field(..., description="Result message")
