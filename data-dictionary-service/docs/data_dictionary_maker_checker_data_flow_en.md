# Data Dictionary Maker-Checker Data Flow

## 1. Purpose

This document explains the role of each maker-checker table and the expected database flow for add, update, delete, approve, and reject operations.

It is intended for:

- backend engineers
- frontend engineers
- BAs
- reviewers

## 2. Table Responsibilities

### 2.1 Current published tables

#### `table_entity`

- Stores the current published dataset records.
- This is the final released dataset state used by read and display flows.
- Only approved changes should be written here.

Important governance fields:

- `version_seq`
- `dictionary_action`
- `approval_status`
- `record_status`
- `effective_from`
- `effective_to`
- `latest_request_id`

#### `attribute_entity`

- Stores the current published attribute records.
- This is the final released attribute state used by read and display flows.
- Only approved changes should be written here.

Important governance fields:

- `version_seq`
- `dictionary_action`
- `approval_status`
- `record_status`
- `effective_from`
- `effective_to`
- `latest_request_id`

### 2.2 Approval header table

#### `approval_request`

- Represents one maker submit action.
- One `Submit` action should generate one `request_id`.
- A request can contain one or many dataset / attribute changes.
- Dashboard tabs should primarily query this table at request level.

Important fields:

- `request_id`
- `source_type`
- `domain_id`
- `tenant_unique_id`
- `submitted_by`
- `submitted_at`
- `maker_comment`
- `request_status`
- `reviewed_by`
- `reviewed_at`
- `checker_comment`
- `total_items`
- `approved_items`
- `rejected_items`

### 2.3 Pending tables

#### `table_entity_pending`

- Stores pending dataset changes waiting for approval.
- Each row represents one dataset-level pending item under one request.
- Used as request detail data in the dashboard.

#### `attribute_entity_pending`

- Stores pending attribute changes waiting for approval.
- Each row represents one attribute-level pending item under one request.
- Used as request detail data in the dashboard.

Important shared fields in pending tables:

- `request_id`
- `target_*_id`
- `dictionary_action`
- `approval_status`
- `current_version_seq`
- `target_version_seq`
- `requester_id`
- `requester_ts`
- `approver_id`
- `approver_ts`
- `maker_comment`
- `checker_comment`
- `current_snapshot`
- `validation_errors`

### 2.4 History tables

#### `table_entity_history`

- Stores archived dataset versions.
- Used when an approved update or delete closes a previous version.

#### `attribute_entity_history`

- Stores archived attribute versions.
- Used when an approved update or delete closes a previous version.

### 2.5 Access control mapping table

#### `tenant_role_mapping`

- Stores tenant-level AD group mapping for requester / approver / viewer roles.
- Used for role evaluation.
- Does not store request or pending data.

## 3. General Lifecycle Rule

The core rule is:

1. Maker submits a change.
2. Data is first written to `approval_request` and pending tables.
3. Current published tables are not changed at submit time.
4. Checker approve or reject decides whether the change is released.

That means:

- `approval_request` and pending tables represent in-flight work
- current tables represent released state
- history tables represent closed prior versions

## 4. Add Flow

Scenario:

- maker adds one dataset
- maker adds the related attributes

### 4.1 Maker submit

#### Step 1: create request header

Insert one row into `approval_request`.

Typical values:

- `request_id = new UUID`
- `source_type = 'UI'` or `'UPLOAD'`
- `domain_id = target domain`
- `tenant_unique_id = target tenant`
- `submitted_by = maker employee id`
- `submitted_at = now()`
- `maker_comment = submit comment`
- `request_status = 'PENDING'`
- `total_items = 1 + number of attributes`

#### Step 2: create dataset pending row

Insert one row into `table_entity_pending`.

Typical values:

- `request_id = request header id`
- `target_table_id = NULL` or pre-generated dataset id
- `dictionary_action = 'A'`
- `approval_status = 'P'`
- `current_version_seq = NULL`
- `target_version_seq = 1`
- `requester_id = maker`
- `requester_ts = now()`
- `current_snapshot = NULL`
- `table_metadata = proposed dataset payload`

#### Step 3: create attribute pending rows

Insert one row into `attribute_entity_pending` per new attribute.

Typical values:

- `request_id = same request id`
- `target_attribute_id = NULL` or pre-generated attribute id
- `dictionary_action = 'A'`
- `approval_status = 'P'`
- `current_version_seq = NULL`
- `target_version_seq = 1`
- `requester_id = maker`
- `requester_ts = now()`
- `current_snapshot = NULL`
- `metadata = proposed attribute payload`

### 4.2 Pending Requests display

After submit:

- the request is visible because `approval_request.request_status = 'PENDING'`
- request details come from `table_entity_pending` and `attribute_entity_pending`

### 4.3 Checker approve

#### Step 1: update request header

Update `approval_request`:

- `request_status = 'APPROVED'`
- `reviewed_by = checker`
- `reviewed_at = now()`
- `checker_comment = checker comment`
- `approved_items = total_items`
- `rejected_items = 0`

#### Step 2: publish dataset to current table

Insert one row into `table_entity`.

Typical values:

- `id = target_table_id or new id`
- `version_seq = 1`
- `dictionary_action = 'A'`
- `approval_status = 'A'`
- `record_status = 'A'`
- `requester_id = maker`
- `approver_id = checker`
- `requester_ts = submit time`
- `approver_ts = approve time`
- `effective_from = approve time`
- `effective_to = NULL`
- `latest_request_id = request_id`
- `table_metadata = approved pending payload`

#### Step 3: publish attributes to current table

Insert rows into `attribute_entity`.

Typical values:

- `version_seq = 1`
- `dictionary_action = 'A'`
- `approval_status = 'A'`
- `record_status = 'A'`
- `effective_from = approve time`
- `effective_to = NULL`
- `latest_request_id = request_id`

#### Step 4: update pending rows

Update related pending rows:

- `approval_status = 'A'`
- `approver_id = checker`
- `approver_ts = now()`
- `checker_comment = checker comment`

Pure add usually does not require history rows because there is no prior version to close.

### 4.4 Checker reject

Reject does not publish anything to current tables.

Update only:

- `approval_request.request_status = 'REJECTED'`
- request review fields
- pending `approval_status = 'R'`
- pending review fields

Current tables and history tables remain unchanged.

## 5. Update Flow

Scenario:

- maker updates an existing dataset
- or maker updates an existing attribute

### 5.1 Maker submit

#### Step 1: create request header

Insert one row into `approval_request`.

#### Step 2: create dataset update pending row

Insert one row into `table_entity_pending`.

Typical values:

- `target_table_id = existing dataset id`
- `dictionary_action = 'U'`
- `approval_status = 'P'`
- `current_version_seq = current version`
- `target_version_seq = current version + 1`
- `current_snapshot = current published dataset snapshot`
- `table_metadata = updated dataset payload`

#### Step 3: create attribute update pending rows

Insert one row into `attribute_entity_pending` for each changed attribute.

Typical values:

- `target_attribute_id = existing attribute id`
- `dictionary_action = 'U'`
- `approval_status = 'P'`
- `current_version_seq = current version`
- `target_version_seq = current version + 1`
- `current_snapshot = current published attribute snapshot`
- `metadata = updated attribute payload`

This is what enables old-versus-new comparison in the dashboard.

### 5.2 Checker approve

#### Step 1: update request header

Update `approval_request` to approved.

#### Step 2: archive old dataset version

Insert one row into `table_entity_history`.

Typical values:

- `table_id = current dataset id`
- `table_metadata = old current payload`
- `version_seq = old version`
- `effective_from = old current effective_from`
- `effective_to = approve time`
- `source_request_id = request_id`

#### Step 3: update current dataset row

Update `table_entity`:

- `table_metadata = approved new payload`
- `version_seq = target_version_seq`
- `dictionary_action = 'U'`
- `approval_status = 'A'`
- `record_status = 'A'`
- `requester_id = maker`
- `approver_id = checker`
- `requester_ts = submit time`
- `approver_ts = approve time`
- `effective_from = approve time`
- `effective_to = NULL`
- `latest_request_id = request_id`

#### Step 4: archive old attribute versions and update current attributes

For each changed attribute:

1. insert the old current row into `attribute_entity_history`
2. update the `attribute_entity` current row to the approved version

### 5.3 Checker reject

Reject updates only:

- `approval_request`
- pending rows

Current tables and history tables remain unchanged.

## 6. Delete Flow

Scenario:

- maker deletes a dataset

Latest clarified rule:

- once dataset delete is approved, all attributes under that dataset must also be soft deleted

### 6.1 Maker submit

#### Step 1: create request header

Insert one row into `approval_request`.

#### Step 2: create dataset delete pending row

Insert one row into `table_entity_pending`.

Typical values:

- `target_table_id = existing dataset id`
- `dictionary_action = 'D'`
- `approval_status = 'P'`
- `current_version_seq = current dataset version`
- `current_snapshot = current published dataset snapshot`
- `table_metadata = current payload or delete-marked payload`

#### Step 3: do not create child attribute delete pending rows

Based on the latest clarified rule:

- dataset delete submit does not create separate attribute delete requests
- the submit stage only writes the dataset-level delete pending item

Reason:

- one dataset may have many attributes
- generating pending rows for every child attribute would make the request unnecessarily heavy
- child attribute soft delete is handled later during approve publish

### 6.2 Checker approve

#### Step 1: update request header

Update `approval_request` to approved.

#### Step 2: soft delete current dataset row

Update `table_entity`:

- `dictionary_action = 'D'`
- `record_status = 'D'`
- `approval_status = 'A'`
- `approver_id = checker`
- `approver_ts = approve time`
- `latest_request_id = request_id`

Depending on the final versioning strategy:

- either keep the current row as a disabled current state
- or archive the prior version and treat delete as version closure

#### Step 3: soft delete all related attributes

For all current attributes under the dataset:

- update `attribute_entity.record_status = 'D'`
- update `attribute_entity.dictionary_action = 'D'`
- update `attribute_entity.approval_status = 'A'`
- update `attribute_entity.approver_id = checker`
- update `attribute_entity.approver_ts = approve time`
- update `attribute_entity.latest_request_id = request_id`

This must be enforced explicitly by application publish logic.

It is not automatically guaranteed by the schema.

#### Step 4: write history when needed

Write dataset and attribute history rows whenever the prior active version needs to be preserved as a closed historical version.

### 6.3 Checker reject

Reject updates only:

- `approval_request`
- pending rows

Current tables and history tables remain unchanged.

## 7. Dashboard Tab Mapping

Dashboard list tabs should be driven primarily by `approval_request`.

Pending tables should be used for request detail expansion rather than as the primary tab list source.

### 7.1 Anonymous user

- can enter dashboard
- `Pending Requests`: all requests where `request_status = 'PENDING'`
- `My Requests`: not shown

### 7.2 Logged-in maker

- `Pending Requests`: requests submitted by the current user where `request_status = 'PENDING'`
- `My Requests`: requests submitted by the current user where `request_status IN ('APPROVED', 'REJECTED', 'PARTIALLY_APPROVED')`

### 7.3 Logged-in checker

- `Pending Requests`: pending requests within the checker's approver tenant scope
- `My Requests`: requests submitted by the current user where `request_status IN ('APPROVED', 'REJECTED', 'PARTIALLY_APPROVED')`

### 7.4 Logged-in user who is both maker and checker

- `Pending Requests`: union of
  - the current user's submitted pending requests
  - pending requests waiting for approval in the user's checker scope
- `My Requests`: requests submitted by the current user where `request_status IN ('APPROVED', 'REJECTED', 'PARTIALLY_APPROVED')`

Pending request results should be deduplicated by `request_id`.

## 8. Key Implementation Notes

### 8.1 Request-level query versus item-level query

`approval_request` is the correct primary source for dashboard tabs.

Pending tables are item-level detail tables and should not be used directly as the tab list source.

### 8.2 Delete cascade is application logic

The rule "approved dataset delete soft deletes all child attributes" is not automatically enforced by foreign keys or constraints.

It must be handled explicitly in the approval publish transaction.

### 8.3 Version and history behavior

- add: publish directly into current, no old version to archive
- update: old current goes to history, new approved version replaces current
- delete: current becomes disabled, and child attributes also become disabled

## 9. Summary

The model should be understood in this way:

- `approval_request`: one submit action
- `table_entity_pending` / `attribute_entity_pending`: pending detail items
- `table_entity` / `attribute_entity`: published current data
- `table_entity_history` / `attribute_entity_history`: archived versions
- `tenant_role_mapping`: tenant role mapping

The lifecycle is:

1. maker submits
2. request header and pending rows are created
3. checker reviews
4. approve publishes to current and archives history when needed
5. reject only changes request and pending statuses
