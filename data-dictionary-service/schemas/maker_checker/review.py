from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


ReviewAction = Literal["APPROVE", "REJECT"]
ReviewItemType = Literal["DATASET", "ATTRIBUTE"]
ReviewItemTypeScope = Literal["DATASET", "ATTRIBUTE", "ALL"]
ApprovalRequestStatus = Literal["PENDING", "IN_REVIEW", "APPROVED", "REJECTED", "COMPLETED_MIXED"]
ProcessedItemStatus = Literal["APPROVED", "REJECTED"]


class ReviewItemSelection(BaseModel):
    itemType: ReviewItemType = Field(..., description="Pending item type")
    pendingId: str = Field(..., description="Pending row id")


class ReviewRequestSelection(BaseModel):
    requestId: str = Field(..., description="Approval request id")
    itemTypeScope: ReviewItemTypeScope = Field(..., description="Dashboard tab scope")


class ReviewRequest(BaseModel):
    items: List[ReviewItemSelection] = Field(default_factory=list)
    requests: List[ReviewRequestSelection] = Field(default_factory=list)
    checkerComment: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def validate_selection(self):
        if not self.items and not self.requests:
            raise ValueError("At least one item or request selection is required")

        item_keys = {(item.itemType, item.pendingId) for item in self.items}
        if len(item_keys) != len(self.items):
            raise ValueError("Duplicate pending item selection found")

        request_keys = {(request.requestId, request.itemTypeScope) for request in self.requests}
        if len(request_keys) != len(self.requests):
            raise ValueError("Duplicate request selection found")

        return self


class ProcessedReviewItem(BaseModel):
    itemType: ReviewItemType
    pendingId: str
    status: ProcessedItemStatus


class FailedReviewItem(BaseModel):
    itemType: ReviewItemType
    pendingId: str
    requestId: Optional[str] = None
    code: str
    message: str


class ProcessedRequest(BaseModel):
    requestId: str
    requestStatus: ApprovalRequestStatus
    approvedItems: int
    rejectedItems: int
    pendingItems: int
    processedItems: List[ProcessedReviewItem] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    processedRequests: List[ProcessedRequest] = Field(default_factory=list)
    failedItems: List[FailedReviewItem] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
