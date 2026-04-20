from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, root_validator


DictionaryAction = Literal["A", "U", "D"]
SourceType = Literal["UI"]


class DatasetSubmitItem(BaseModel):
    clientRef: Optional[str] = Field(default=None, description="Client-side temporary ref for new dataset items")
    action: DictionaryAction = Field(..., description="Dataset action: A/U/D")
    entityId: Optional[str] = Field(default=None, description="Current dataset id. Required for U/D")
    tableMetadata: Dict[str, Any] = Field(default_factory=dict, description="Dataset payload")
    currentVersionSeq: Optional[int] = Field(default=None, description="Current version for optimistic checks")

    @root_validator
    def validate_entity_id(cls, values):
        if values.get("action") in {"U", "D"} and not values.get("entityId"):
            raise ValueError("entityId is required for dataset update/delete")
        return values


class AttributeSubmitItem(BaseModel):
    datasetClientRef: Optional[str] = Field(default=None, description="Client-side ref to a new dataset in the same submit")
    action: DictionaryAction = Field(..., description="Attribute action: A/U/D")
    entityId: Optional[str] = Field(default=None, description="Current attribute id. Required for U/D")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Attribute payload")
    currentVersionSeq: Optional[int] = Field(default=None, description="Current version for optimistic checks")

    @root_validator
    def validate_entity_id(cls, values):
        if values.get("action") in {"U", "D"} and not values.get("entityId"):
            raise ValueError("entityId is required for attribute update/delete")
        return values


class SubmitRequest(BaseModel):
    sourceType: SourceType = Field(default="UI", description="Source type for submit API")
    domainId: str = Field(..., description="Target domain id")
    tenantUniqueId: str = Field(..., description="Target tenant unique id")
    makerComment: Optional[str] = Field(default=None, description="Maker request-level comment")
    dataset: Optional[DatasetSubmitItem] = Field(default=None, description="Deprecated single dataset field for backward compatibility")
    datasets: List[DatasetSubmitItem] = Field(default_factory=list, description="Dataset-level changes in this submit")
    attributes: List[AttributeSubmitItem] = Field(default_factory=list, description="Attribute-level changes from current page")

    @root_validator(pre=True)
    def normalize_datasets(cls, values):
        dataset = values.get("dataset")
        datasets = values.get("datasets")

        if dataset is not None and datasets:
            raise ValueError("Use either dataset or datasets, not both")

        if dataset is not None:
            values["datasets"] = [dataset]
        elif datasets is None:
            values["datasets"] = []

        return values

    @root_validator
    def validate_non_empty(cls, values):
        if not values.get("datasets") and not values.get("attributes"):
            raise ValueError("At least one dataset or attribute change is required")
        return values


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
