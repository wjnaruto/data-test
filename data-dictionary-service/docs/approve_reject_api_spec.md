# Approve / Reject API Spec

## 1. Purpose

The approve / reject APIs are used by the Approver Dashboard to review maker-checker pending items.

The APIs review at pending-item level internally, but the request body supports both direct item selection and request-level selection from a dashboard tab. One API call can process:

- one pending item
- multiple pending items under one request
- multiple pending items across multiple requests
- one or more request rows selected from the dataset tab
- one or more request rows selected from the attribute tab

The implementation must always expand the caller's selection into concrete pending items, group them by `request_id`, and process each request group in its own transaction.

## 2. Scope

The APIs support pending items from:

- `table_entity_pending`
- `attribute_entity_pending`

They update:

- `approval_request`
- `table_entity_pending`
- `attribute_entity_pending`
- `table_entity`
- `attribute_entity`
- `table_entity_history`
- `attribute_entity_history`

`REJECT` does not update current main tables and does not write history records.

## 3. Endpoint Design

### 3.1 Approve

`POST /api/v1/review/approve`

### 3.2 Reject

`POST /api/v1/review/reject`

Both endpoints use the same request and response schema.

## 4. Authentication and Authorization

### 4.1 Authentication

Both APIs require:

```http
Authorization: Bearer <access_token>
```

The token is validated by the shared access control layer:

- `services/access_control.py`
- `get_current_access_context`

### 4.2 Approver Role Validation

For every pending item being reviewed:

1. Load the parent `approval_request`.
2. Read `tenant_unique_id` from the request.
3. Validate the current user has `APPROVER` role for that tenant.
4. Reject the operation with `403` if the user does not have approver role.

The role source is `tenant_role_mapping`, resolved from JWT `groups`.

### 4.3 Self-Approval Prevention

If the current user is also the maker of the request:

```text
approval_request.submitted_by == current_user.user_id
```

then the user cannot approve or reject any pending item in that request.

Return:

```http
403 Forbidden
```

with error code:

```text
SELF_REVIEW_NOT_ALLOWED
```

## 5. Request Body

The API supports two selection modes:

- `items`: explicit pending item selection
- `requests`: request-level selection within a dashboard tab

At least one of `items` or `requests` must be provided.

### 5.1 Explicit Pending Item Selection

```json
{
  "items": [
    {
      "itemType": "DATASET",
      "pendingId": "table-pending-id-001"
    },
    {
      "itemType": "ATTRIBUTE",
      "pendingId": "attribute-pending-id-001"
    }
  ],
  "checkerComment": "Approved after review"
}
```

### 5.2 Request-Level Tab Selection

When the frontend user selects a request row from the dataset tab or attribute tab, the frontend does not need to send every pending item id.

Instead, it sends the `requestId` and the tab scope:

```json
{
  "requests": [
    {
      "requestId": "req-001",
      "itemTypeScope": "DATASET"
    },
    {
      "requestId": "req-002",
      "itemTypeScope": "ATTRIBUTE"
    }
  ],
  "checkerComment": "Approved selected request rows"
}
```

The backend expands each request selection into pending rows:

| `itemTypeScope` | Expanded pending rows |
| --- | --- |
| `DATASET` | All `table_entity_pending` rows for the request where `approval_status = 'P'` |
| `ATTRIBUTE` | All `attribute_entity_pending` rows for the request where `approval_status = 'P'` |
| `ALL` | All pending dataset and attribute rows for the request. This is mainly for backend/admin use or future UI support. |

For the current UI:

- dataset tab should send `itemTypeScope = DATASET`
- attribute tab should send `itemTypeScope = ATTRIBUTE`

This matters for bulk upload. A single bulk upload request may contain both dataset and attribute pending rows. If the user approves that request from the dataset tab, only the dataset pending rows in that request are approved. Attribute rows remain pending unless they are selected from the attribute tab or included through `ALL`.

### 5.3 Fields

| Field | Required | Description |
| --- | --- | --- |
| `items` | Conditional | Explicit pending items to review. |
| `items[].itemType` | Yes | `DATASET` or `ATTRIBUTE`. |
| `items[].pendingId` | Yes | Pending row primary key. |
| `requests` | Conditional | Request-level selections from dashboard tabs. |
| `requests[].requestId` | Yes | Approval request id. |
| `requests[].itemTypeScope` | Yes | `DATASET`, `ATTRIBUTE`, or `ALL`. |
| `checkerComment` | Optional for approve, recommended for reject | Checker-level comment stored on pending rows and request header. |

### 5.4 Request Rules

- Duplicate explicit pending items in the same request body are rejected with `400`.
- Duplicate request-level selections with the same `requestId` and `itemTypeScope` are rejected with `400`.
- If `items` and `requests` overlap after expansion, the duplicated pending item is processed once.
- All pending items must still have `approval_status = 'P'`.
- Items already approved or rejected are skipped only if explicitly supported later. Initial implementation should reject the request group with `409`.
- The same request body may contain dataset and attribute pending items.
- If a request-level selection expands to zero pending rows, return `409` with `NO_PENDING_ITEMS_FOR_SELECTION`.

## 6. Response Body

```json
{
  "processedRequests": [
    {
      "requestId": "req-001",
      "requestStatus": "IN_REVIEW",
      "approvedItems": 2,
      "rejectedItems": 0,
      "pendingItems": 3,
      "processedItems": [
        {
          "itemType": "DATASET",
          "pendingId": "table-pending-id-001",
          "status": "APPROVED"
        },
        {
          "itemType": "ATTRIBUTE",
          "pendingId": "attribute-pending-id-001",
          "status": "APPROVED"
        }
      ]
    }
  ],
      "failedItems": []
}
```

### 6.1 Response Fields

| Field | Description |
| --- | --- |
| `processedRequests` | Request-level processing result grouped by `request_id`. |
| `requestStatus` | Recalculated `approval_request.request_status`. |
| `approvedItems` | Current approved item count for the request after review. |
| `rejectedItems` | Current rejected item count for the request after review. |
| `pendingItems` | Remaining pending item count after review. |
| `processedItems` | Items successfully processed in this API call. |
| `failedItems` | Items that failed validation or dependency checks. |

Initial implementation should fail a request group atomically. If one item in a request group fails, no item in that request group should be committed.

### 6.2 Expanded Selection Response

If the request used request-level tab selection, the response should still return concrete processed pending items after expansion. This lets the frontend refresh the selected tab without guessing which rows changed.

## 7. Request Status State Machine

Because review happens at pending-item level, `approval_request.request_status` must represent partial review state.

Recommended values:

| Status | Meaning |
| --- | --- |
| `PENDING` | All items are still pending. No item has been reviewed. |
| `IN_REVIEW` | Some items have been approved/rejected, but at least one item is still pending. |
| `APPROVED` | All items are reviewed and all are approved. |
| `REJECTED` | All items are reviewed and all are rejected. |
| `COMPLETED_MIXED` | All items are reviewed, with a mix of approved and rejected items. |

### 7.1 Migration Note

The current `approval_request_status_chk` constraint must be updated before implementing this API.

Current model allows:

```text
PENDING, APPROVED, REJECTED, PARTIALLY_APPROVED
```

Target allowed values:

```text
PENDING, IN_REVIEW, APPROVED, REJECTED, COMPLETED_MIXED
```

### 7.2 Header Status Recalculation

After each request group is processed, recalculate the header from item counts.

Let:

```text
total_items = approval_request.total_items
approved_items = count(table pending A) + count(attribute pending A)
rejected_items = count(table pending R) + count(attribute pending R)
pending_items = total_items - approved_items - rejected_items
```

Rules:

| Condition | request_status |
| --- | --- |
| `approved_items = 0`, `rejected_items = 0`, `pending_items > 0` | `PENDING` |
| `pending_items > 0`, and at least one item is approved/rejected | `IN_REVIEW` |
| `approved_items = total_items` | `APPROVED` |
| `rejected_items = total_items` | `REJECTED` |
| `pending_items = 0`, `approved_items > 0`, `rejected_items > 0` | `COMPLETED_MIXED` |

## 8. Pending Item Status

Pending item status is stored in:

- `table_entity_pending.approval_status`
- `attribute_entity_pending.approval_status`

Allowed values:

| Value | Meaning |
| --- | --- |
| `P` | Pending |
| `A` | Approved |
| `R` | Rejected |

## 9. Approve Flow

### 9.1 Common Approve Flow

For each `request_id` group:

1. Open a DB transaction.
2. Load and lock the `approval_request` row.
3. Load and lock selected pending rows.
4. Validate the current user has approver role for the request tenant.
5. Validate the current user is not the maker of the same request.
6. Validate all selected pending rows are still `approval_status = 'P'`.
7. Expand request-level selections into concrete pending items if `requests` was provided.
8. Validate dependency rules.
9. Process dataset pending items.
10. Process attribute pending items.
11. Mark selected pending rows as approved.
12. Recalculate request header status and item counts.
13. Commit.

### 9.2 Processing Order

Within one request group, process in this order:

1. Dataset `A`
2. Dataset `U`
3. Attribute `A`
4. Attribute `U`
5. Attribute `D`
6. Dataset `D`

Reason:

- New attributes may depend on new datasets.
- Dataset delete cascades to child attributes and should run after selected child attribute items are handled or rejected by validation.

## 10. Dataset Approve Rules

### 10.1 Dataset Add

Input:

- `table_entity_pending.dictionary_action = 'A'`
- `target_table_id IS NULL`
- proposed table id is stored in `table_entity_pending.table_metadata ->> 'id'`

Approve behavior:

1. Insert a new row into `table_entity`.
2. Use `table_metadata` from pending row as the base JSONB.
3. Set governance fields:
   - `requester_id`
   - `approver_id`
   - `requester_ts`
   - `approver_ts`
   - `version_seq = 1`
   - `dictionary_action = 'A'`
   - `approval_status = 'A'`
   - `record_status = 'A'`
   - `effective_from = approver_ts`
   - `effective_to = NULL`
   - `latest_request_id = request_id`
4. Mark pending row approved.

History:

- Do not write `table_entity_history` for add because there is no previous active version.

### 10.2 Dataset Update

Input:

- `dictionary_action = 'U'`
- `target_table_id` points to an existing `table_entity.id`

Approve behavior:

1. Load current `table_entity` row.
2. Insert current row into `table_entity_history`.
3. Merge JSONB:

   ```text
   final_table_metadata = current_table_metadata + pending_table_metadata
   ```

4. Update `table_entity` with merged JSONB.
5. Increment version:

   ```text
   version_seq = current_version_seq + 1
   ```

6. Set governance fields:
   - `requester_id`
   - `approver_id`
   - `requester_ts`
   - `approver_ts`
   - `dictionary_action = 'U'`
   - `approval_status = 'A'`
   - `record_status = 'A'`
   - `effective_from = approver_ts`
   - `effective_to = NULL`
   - `latest_request_id = request_id`
7. Mark pending row approved.

Important:

- Do not overwrite main table JSONB with pending JSONB directly.
- Unchanged JSONB fields from the current main row must remain unchanged.

### 10.3 Dataset Delete

Input:

- `dictionary_action = 'D'`
- `target_table_id` points to an existing `table_entity.id`

Approve behavior:

1. Load current `table_entity` row.
2. Insert current dataset row into `table_entity_history`.
3. Load all active child attributes for that dataset.
4. Insert each active child attribute into `attribute_entity_history`.
5. Soft delete the dataset in `table_entity`.
6. Soft delete all active child attributes in `attribute_entity`.
7. Mark dataset pending row approved.

Soft delete fields:

- `dictionary_action = 'D'`
- `approval_status = 'A'`
- `record_status = 'D'`
- `approver_id = current user`
- `approver_ts = now`
- `effective_to = now`
- JSONB should set:
  - `deleted = true`
  - `updatedAt = now in milliseconds`
  - `updatedBy = approver id`

No separate child attribute pending rows are required for dataset delete.

## 11. Attribute Approve Rules

### 11.1 Attribute Add

Input:

- `attribute_entity_pending.dictionary_action = 'A'`
- `target_attribute_id IS NULL`
- proposed attribute id is stored in `attribute_entity_pending.metadata ->> 'id'`
- parent table id is stored in `attribute_entity_pending.metadata ->> 'tableId'`

Approve behavior:

1. Validate parent dataset exists in `table_entity`.
2. If parent dataset is also a new dataset in the same request and selected in this approve call, insert the dataset first.
3. If parent dataset is a new dataset in the same request but is not yet approved or selected in this approve call, reject with dependency error.
4. Insert new row into `attribute_entity`.
5. Set governance fields:
   - `version_seq = 1`
   - `dictionary_action = 'A'`
   - `approval_status = 'A'`
   - `record_status = 'A'`
   - requester/approver fields
   - `effective_from = approver_ts`
   - `latest_request_id = request_id`
6. Mark pending row approved.

History:

- Do not write `attribute_entity_history` for add because there is no previous active version.

### 11.2 Attribute Update

Input:

- `dictionary_action = 'U'`
- `target_attribute_id` points to an existing `attribute_entity.id`

Approve behavior:

1. Load current `attribute_entity` row.
2. Insert current row into `attribute_entity_history`.
3. Merge JSONB:

   ```text
   final_metadata = current_metadata + pending_metadata
   ```

4. Update `attribute_entity` with merged JSONB.
5. Increment version.
6. Set governance fields.
7. Mark pending row approved.

Important:

- Do not overwrite current attribute JSONB with pending JSONB directly.
- Unchanged JSONB values must remain unchanged.

### 11.3 Attribute Delete

Input:

- `dictionary_action = 'D'`
- `target_attribute_id` points to an existing `attribute_entity.id`

Approve behavior:

1. Load current `attribute_entity` row.
2. Insert current row into `attribute_entity_history`.
3. Soft delete current row in `attribute_entity`.
4. Mark pending row approved.

Soft delete fields:

- `dictionary_action = 'D'`
- `approval_status = 'A'`
- `record_status = 'D'`
- `effective_to = now`
- JSONB should set:
  - `deleted = true`
  - `updatedAt = now in milliseconds`
  - `updatedBy = approver id`

## 12. Reject Flow

### 12.1 Common Reject Flow

For each `request_id` group:

1. Open a DB transaction.
2. Load and lock the `approval_request` row.
3. Load and lock selected pending rows.
4. Validate approver role.
5. Validate self-review prevention.
6. Validate all selected pending rows are still pending.
7. Mark selected pending rows rejected.
8. Recalculate request header status and item counts.
9. Commit.

### 12.2 Reject Data Rules

Reject updates:

- `table_entity_pending.approval_status = 'R'`
- `attribute_entity_pending.approval_status = 'R'`
- `approver_id`
- `approver_ts`
- `checker_comment`
- `updated_at`
- `approval_request` reviewed fields and status summary

Reject does not update:

- `table_entity`
- `attribute_entity`
- `table_entity_history`
- `attribute_entity_history`

Reason:

- Rejected changes were never published.
- History tables should represent closed published versions, not rejected proposals.

## 13. Bulk Upload Dependency Rules

Bulk upload can create one `approval_request` containing both dataset and attribute pending rows.

### 13.1 New Dataset With New Attributes

If a new attribute points to a new dataset from the same request:

- It can be approved only if the parent dataset is approved first.
- It can be approved in the same API call as the parent dataset.
- It cannot be approved alone before the parent dataset exists in `table_entity`.

### 13.2 Partial Review Example

Request contains:

- dataset add `table_pending_1`
- attribute add `attribute_pending_1`
- attribute add `attribute_pending_2`

Allowed:

```json
{
  "items": [
    {"itemType": "DATASET", "pendingId": "table_pending_1"},
    {"itemType": "ATTRIBUTE", "pendingId": "attribute_pending_1"}
  ]
}
```

This inserts the dataset first, then inserts the selected attribute.

Not allowed:

```json
{
  "items": [
    {"itemType": "ATTRIBUTE", "pendingId": "attribute_pending_1"}
  ]
}
```

if the parent dataset is not already in `table_entity`.

Return:

```http
409 Conflict
```

with error code:

```text
PARENT_DATASET_NOT_APPROVED
```

### 13.3 Request-Level Selection in Bulk Upload

For bulk upload, one request may contain both dataset and attribute pending rows.

If the user selects the request row in the dataset tab:

```json
{
  "requests": [
    {"requestId": "bulk_req_001", "itemTypeScope": "DATASET"}
  ],
  "checkerComment": "Approve dataset rows only"
}
```

The backend approves only `table_entity_pending` rows for `bulk_req_001`.

If the user selects the request row in the attribute tab:

```json
{
  "requests": [
    {"requestId": "bulk_req_001", "itemTypeScope": "ATTRIBUTE"}
  ],
  "checkerComment": "Approve attribute rows only"
}
```

The backend approves only `attribute_entity_pending` rows for `bulk_req_001`.

If the attribute rows depend on a newly added dataset from the same bulk request and that dataset is not already approved into `table_entity`, the attribute review fails with `PARENT_DATASET_NOT_APPROVED`.

### 13.4 Dataset Delete With Child Attribute Pending Items

If a dataset delete is selected and there are still pending attribute items under that dataset:

- Initial implementation should reject this review operation with `409`.
- The checker should resolve child attribute pending items first, or reject them together depending on dashboard UX.

This avoids double-processing attribute state during dataset delete cascade.

## 14. JSONB Merge Rules

### 14.1 Add

For add actions:

```text
main_jsonb = pending_jsonb
```

because there is no existing main row.

### 14.2 Update

For update actions:

```text
main_jsonb = current_main_jsonb + pending_jsonb
```

The pending JSONB only overrides changed keys. Current main JSONB values that are not changed must stay unchanged.

### 14.3 Delete

For delete actions:

Do not replace the current JSONB with pending JSONB.

Only set control fields:

- `deleted = true`
- `updatedAt = now in milliseconds`
- `updatedBy = approver id`

## 15. Error Responses

### 15.1 400 Bad Request

Use for invalid request shape:

- empty `items`
- duplicate pending item
- unsupported `itemType`
- missing `pendingId`

### 15.2 401 Unauthorized

Use for:

- missing bearer token
- invalid JWT
- expired JWT

### 15.3 403 Forbidden

Use for:

- user does not have approver role for the request tenant
- user tries to approve/reject their own request

Suggested error codes:

- `APPROVER_ROLE_REQUIRED`
- `SELF_REVIEW_NOT_ALLOWED`

### 15.4 404 Not Found

Use for:

- pending item not found
- parent approval request not found
- current main row not found for update/delete

### 15.5 409 Conflict

Use for:

- pending item is already approved/rejected
- parent dataset for attribute add is not approved or not selected in the same approve call
- dataset delete conflicts with selected or unresolved child attribute pending items
- request-level tab selection expands to no pending items

Suggested error codes:

- `PENDING_ITEM_ALREADY_REVIEWED`
- `PARENT_DATASET_NOT_APPROVED`
- `DATASET_DELETE_HAS_PENDING_ATTRIBUTES`
- `NO_PENDING_ITEMS_FOR_SELECTION`

## 16. Implementation Plan

### 16.1 New Files

Recommended files:

- `schemas/maker_checker/review.py`
- `api/maker_checker/review_api.py`
- `services/maker_checker/review_service.py`

### 16.2 Repository Extensions

Extend repositories with:

- load table pending rows by pending ids with row lock
- load attribute pending rows by pending ids with row lock
- load pending rows by `request_id` and item type scope with row lock
- update table pending status
- update attribute pending status
- insert table history
- insert attribute history
- insert/update/soft-delete current table entity
- insert/update/soft-delete current attribute entity
- recalculate approval request status and counts

### 16.3 Shared Service Functions

Recommended service-level helpers:

- `group_items_by_request`
- `validate_approver_access`
- `validate_self_review`
- `validate_pending_status`
- `validate_approve_dependencies`
- `merge_table_metadata`
- `merge_attribute_metadata`
- `mark_items_approved`
- `mark_items_rejected`
- `recalculate_request_header`

## 17. Final Review Behavior Summary

### Approve

Approve publishes selected pending items.

It may:

- insert current rows for add
- archive old current rows to history for update/delete
- update current rows for update
- soft delete current rows for delete
- update pending rows to `A`
- recalculate approval request status

### Reject

Reject does not publish selected pending items.

It only:

- updates selected pending rows to `R`
- records checker information
- recalculates approval request status

### Request Header

The request header is always derived from item statuses after every review operation.

The API must not trust a client-provided request-level final status.
