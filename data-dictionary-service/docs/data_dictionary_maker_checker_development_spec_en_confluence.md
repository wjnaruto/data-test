# Data Dictionary Service Maker-Checker Development Specification

## 1. Document Information

- Purpose: This document turns the raw requirement into a formal development specification for frontend, backend, QA, Tech Lead, and BA/PO use.
- Scope: Phase 1 Maker-Checker enhancement for Data Dictionary Service.
- Target audience: Frontend, Backend, QA, Tech Lead, BA/PO.
- Source documents:
  - `docs/data_dictionary_requirements_raw_transcription.md`
  - `docs/data_dictionary_requirements_bilingual.md`
  - `docs/data_dictionary_maker_checker_breakdown.md`

## 2. Requirement Summary

### 2.1 Background

The current Data Dictionary Service mainly provides:

- manual metadata upload for producer tenants
- UI-based data dictionary display
- open read access without mandatory login

The core goal of this enhancement is to:

- introduce a Maker-Checker governance flow into the Data Dictionary
- make add, update, delete, and bulk upload changes go through approval before being published
- enforce tenant-level access control through AD groups
- introduce versioning, history, and audit capability

### 2.2 Business Objectives

- improve the accuracy, completeness, and traceability of data dictionary entries
- clearly separate Maker and Checker responsibilities
- enable self-service updates without directly changing published production-visible data
- establish an auditable, traceable, versioned data dictionary management process

### 2.3 Role Definitions

- `Anonymous / Read-only User`
  - can browse and search only
  - cannot perform write actions
- `Requester / Maker`
  - initiates bulk upload or UI row-level maintenance
  - submits changes for approval
  - can view their own requests and approval results
- `Approver / Checker`
  - reviews pending requests
  - approves or rejects changes
  - cannot approve their own requests
- `Viewer`
  - can only view approval records, statuses, and history
  - cannot approve or reject

### 2.4 Phase 1 Scope

- tenant-level AD group authorization
- login triggered by write actions, while read-only access remains anonymous where possible
- bulk upload template download, upload, validation, staging, and approval
- UI row-level Add / Edit / Delete / Submit
- Approver Dashboard
- post-approval publish logic
- version management, history management, and audit logging
- basic search enhancement and Help content enhancement

### 2.5 Suggested Phase 2 or Open Scope

- whether email notification is part of phase 1
- whether advanced search is part of phase 1
- whether `partial approval` is truly in scope for phase 1
- whether `Viewer` must be a dedicated tenant-level AD role

## 3. End-to-End Flow Summary

### 3.1 Read-Only Browsing and Login Trigger Flow

1. The user opens the Data Dictionary page.
2. The user can browse, query, and search without mandatory login.
3. When the user clicks `Upload`, `Add`, `Edit`, `Delete`, `Submit`, `Approve`, or `Reject`, the system checks login state.
4. If the user is not logged in, the frontend shows a login dialog or redirects to the login page.
5. After successful login, the system restores the original user action and continues the flow.

### 3.2 Bulk Upload Flow

1. The Maker downloads the latest template.
2. The Maker fills in the template and sets `Dictionary Action = A/U/D` for each record.
3. The Maker clicks upload and the system validates login state and tenant-level Requester permission.
4. The backend performs file-level and data-level validation.
5. If validation succeeds, the system creates an approval request and writes the records into the approval staging area with status `Pending`.
6. The Approver views the request in the `Pending` tab of the Dashboard.
7. The Approver reviews the request, approves or rejects it, and enters comments.
8. If approved, the system publishes the data into the main table and creates version and audit records.
9. If rejected, the main table remains unchanged and the approval records move to `Rejected`.

### 3.3 UI Row-Level Add / Edit / Delete Flow

1. The user opens the SSD data set page.
2. When the user clicks `Add`, `Edit`, or `Delete`, the system triggers login and permission validation.
3. The user completes row-level changes and clicks `Submit`.
4. The system shows a comments dialog so that the Maker can enter remarks.
5. The backend writes the changes into the approval staging area instead of updating the main table directly.
6. The Approver views the corresponding request in the Dashboard.
7. The Approver reviews and approves or rejects the request.
8. If approved:
   - `A`: create a new active record
   - `U`: close the old version and create a new version
   - `D`: perform soft delete and set `Record Status = D`
9. If rejected, the main table stays unchanged and the request and item statuses move to `Rejected`.

### 3.4 Approver Dashboard Flow

1. The Approver or Viewer opens the Approver Dashboard.
2. The default tab is `Pending`.
3. The `My Requests` tab shows requests submitted by the current user and their statuses.
4. For `Update` records, the page displays old vs new values.
5. The Approver can perform single or bulk approve/reject actions.
6. All approval actions must store checker comments.

### 3.5 Publish, Version, History, and Audit Flow

1. After approval, the system determines the publish behavior based on `Dictionary Action`.
2. For `Add`:
   - a formal version number is assigned only after `validation succeeds + Approver approves`
   - a new record is created in the published data store
   - the version starts from `1.0`
   - `Effective From = approval timestamp`
   - `Effective To = null`
3. For `Update`:
   - a new formal version is created only after `validation succeeds + Approver approves`
   - the current active version gets `Effective To = approval timestamp` to close the old version
   - a new version record is created with sequential version increment, for example `1.0 -> 2.0`
   - the new version gets `Effective From = the same approval timestamp`
   - there must be no overlap between the old and new version validity windows
4. For `Delete`:
   - the raw requirement clearly indicates soft delete / disable rather than physical delete
   - the default interpretation is to update the current active record with `Record Status = D`
   - it is recommended to also close the active period by setting `Effective To = approval timestamp`
   - the current requirement does not explicitly require Delete to create a new version number, so phase 1 should not assume delete-as-new-version unless confirmed by business
5. All approved changes are written into the audit log.

### 3.6 Status Transition Summary

| Scenario | Request Status | Approval Item Status | Main Table Status |
| --- | --- | --- | --- |
| Maker submits successfully | `PENDING` | `P` | unchanged |
| Checker approves all | `APPROVED` | `A` | publish changes |
| Checker rejects all | `REJECTED` | `R` | unchanged |
| Checker partially approves | `PARTIALLY_APPROVED` | mixed `A/R` | publish approved items only |

## 4. Core Business Rules and Design Principles

### 4.1 Authorization Rules

- read operations should remain anonymous where possible
- write operations must require login
- permissions must be checked at tenant level, not only at global role level
- the Approver must belong to the tenant-specific Approver AD group
- the Requester must belong to the tenant-specific Requester AD group
- the Requester and Approver cannot be the same user

### 4.2 Data and Status Rules

- `Dictionary Action`
  - `A` = Add
  - `U` = Update
  - `D` = Delete / Disable
- `Approval Status`
  - `P` = Pending
  - `A` = Approved
  - `R` = Rejected
- `Record Status`
  - `A` = Active
  - `D` = Disabled

### 4.3 Versioning Rules

#### 4.3.1 Timing of Formal Version Number Assignment

- a formal version number is not assigned when the Maker submits data
- a formal version number is assigned only after backend validation succeeds and the Approver approves the change
- pending approval records may carry a candidate version value or no version value, but they must not be treated as published versions

#### 4.3.2 Version Rule for Add

- a new record receives its first formal version only when it is approved
- the initial version always starts from `1.0`
- `Effective From = approval and publish timestamp`
- `Effective To = null`

#### 4.3.3 Version Rule for Update

- a new version is created only when the update is approved
- the new version must increase sequentially from the previous version, for example `1.0 -> 2.0 -> 3.0`
- version numbers cannot be reused or skipped
- before creating the new version, the old version must be closed:
  - old version `Effective To = approval timestamp`
  - new version `Effective From = approval timestamp`

#### 4.3.4 Effective Date Validity Rule

- `Effective From` is the start of a version's validity
- `Effective To` is the end of a version's validity
- the requirement explicitly states that the previous version and the new version must not overlap
- to support same-timestamp handover without overlap, the recommended interpretation is a half-open interval:
  - version validity is interpreted as `[Effective From, Effective To)`
  - if `old Effective To = new Effective From`, there is no overlap

#### 4.3.5 Version Interpretation for Delete

- the raw requirement explicitly states:
  - Delete is soft delete / disable
  - after approval, `Record Status` is updated to `D`
- the raw requirement does not explicitly state that Delete must create a new version number
- therefore, the recommended phase 1 rule is:
  - Delete does not create a new formal version number
  - the current active record is set to `D`
  - it is recommended to also set `Effective To = approval timestamp` to close the record lifecycle
- if the business later wants Delete to create a dedicated disabled version, this should be treated as an explicit requirement extension

#### 4.3.6 History Management Rule

- historical and prior versions must remain traceable
- history can be implemented in one of two ways:
  - Option A: one versioned published table that stores both current and historical versions
  - Option B: a current table plus a dedicated history table
- the raw requirement allows the solution team to recommend the final storage approach
- phase 1 should prioritize the design that best guarantees sequential versioning, non-overlapping validity windows, and simple history retrieval

#### 4.3.7 Technical Recommendation

- avoid treating the displayed version number purely as a string for system calculations
- the recommended design is to maintain an internal numeric revision sequence and expose it externally as `1.0`, `2.0`, `3.0`
- this makes it easier to enforce sequential numbering without reuse or skipping

### 4.4 Data Governance Rules

- before approval, the main table must not be updated directly
- Delete must be implemented as soft delete, not physical delete
- every approved change must create an audit record
- if a pending request already exists for the same business key, duplicate submission should be blocked

### 4.5 Technical Design Recommendations

- the recommended data model is `approval_request`, `approval_item`, and `dictionary_audit_log`
- frontend button visibility should rely on tenant-role information
- the Dashboard should support diff view for Update records
- backend approval, version switching, and publish logic must be handled in a transaction
- version switching should close the old version, create the new version, and write the audit log in the same transaction
- the system must explicitly guarantee that version validity windows do not overlap

### 4.6 Data Model and API Impact Summary

#### Recommended New or Updated Data Stores

| Object | Type | Purpose |
| --- | --- | --- |
| `approval_request` | new table | represents one submission request and stores source, submitter, request status, and comments |
| `approval_item` | new table | represents one pending record under a request and stores action, old/new value, and approval status |
| `dictionary_audit_log` | new table | stores the final audit trail after approval |
| `tenant_role_mapping` | new table or config | maintains tenant to AD group mapping |
| published data table (main/versioned table) | update | add `Requester_ID`, `Approver_ID`, `Version`, `Approval_Status`, `Record_Status`, `Effective_From`, `Effective_To`, and support current/history management |

#### Recommended Versioned Storage Options

| Option | Description | Benefits | Risks / Cost |
| --- | --- | --- | --- |
| Option A: one versioned published table | the same published table stores both current and historical versions, differentiated by `Record_Status`, `Effective_From`, and `Effective_To` | unified structure and natural history queries | current data queries must explicitly filter the active version |
| Option B: current main table + history table | the main table stores only the current active state and prior versions are stored in a dedicated history table | lighter current data queries | more complex publish logic, migration, and history queries |

Recommendation:

- for phase 1, choose the design that most reliably guarantees sequential versions, non-overlapping validity windows, and accessible history
- if current-state read traffic is much higher than history queries and the current main table is already fixed, Option B can be considered
- if implementation simplicity and version consistency are the top priority, Option A is easier to deliver

#### Recommended Backend API Scope

| API Category | Suggested API | Purpose |
| --- | --- | --- |
| Auth | `POST /auth/login` | login |
| Auth | `GET /auth/me` | return current user and tenant-role information |
| Template | `GET /dictionary/templates/latest` | download the latest template |
| Upload | `POST /dictionary/uploads` | upload a template file and create an approval request |
| Submit | `POST /dictionary/changes/submit` | submit UI row-level changes |
| Approval Query | `GET /approvals/pending` | query pending requests |
| Approval Query | `GET /approvals/my-requests` | query My Requests |
| Approval Query | `GET /approvals/{request_id}` | query request details and diff |
| Approval Action | `POST /approvals/{request_id}/approve` | approve a request |
| Approval Action | `POST /approvals/{request_id}/reject` | reject a request |
| History | `GET /dictionary/history/{business_key}` | query version history |
| Audit/Search | `GET /dictionary/audit` | query audit data or extended search results |

## 5. Feature Point Index

| Feature Point ID | Feature Point Name | Description |
| --- | --- | --- |
| `FP-01` | Tenant Role and Auth Foundation | tenant-level role identification, authorization, and login state return model |
| `FP-02` | Lazy Login and Action Resume | write-action login trigger and post-login action recovery |
| `FP-03` | Template and Bulk Upload Entry | template download, upload entry, and upload page enhancement |
| `FP-04` | Bulk Upload Validation and Staging | file parsing, validation, and pending staging |
| `FP-05` | SSD Row-Level Maintenance | row-level add, edit, delete, and submit |
| `FP-06` | Approval Dashboard Query and View | Pending, My Requests, request details, and diff |
| `FP-07` | Approval Actions and Comments | approve, reject, batch actions, and comments |
| `FP-08` | Publish, Version, History, and Audit | publish logic, versioning, history, and audit |
| `FP-09` | Help, Search, and Notification | Help, basic search, and notification hooks |
| `FP-10` | Testing and Rollout Readiness | testing, migration, and go-live readiness |

## 6. Requirement to Feature Overview Matrix

Notes:

- `Suggested Jira` is a recommended story name or naming rule for Jira ticket creation.
- `Actual Jira ID` should be filled by PM or Tech Lead after tickets are created.
- `Status` is intended for ongoing sprint or weekly tracking.

| Req ID | Requirement Item | Objective | Feature Points | Frontend Development Points | Backend Development Points | Suggested FE Jira | Suggested BE Jira | Suggested QA/OPS Jira | Actual Jira ID | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `REQ-01` | Tenant-level identity and authorization control | Ensure only valid users can perform write and approval actions for the correct tenant | `FP-01`, `FP-02` | `FE-01`, `FE-02`, `FE-03` | `BE-01`, `BE-02`, `BE-03`, `BE-04`, `BE-21` | `DDS-MC-FE-01 Lazy login and permission gating` | `DDS-MC-BE-01 Tenant auth and role service` | `DDS-MC-QA-01 Auth and role regression` | `FE:TBD / BE:TBD / QA:TBD` | `Not Started` |
| `REQ-02` | Template download and bulk upload entry enhancement | Provide a standard template and a controlled upload entry point | `FP-03` | `FE-04`, `FE-05`, `FE-06` | `BE-05`, `BE-06` | `DDS-MC-FE-02 Bulk upload page enhancement` | `DDS-MC-BE-02 Template API and file intake` | `DDS-MC-QA-02 Upload entry validation` | `FE:TBD / BE:TBD / QA:TBD` | `Not Started` |
| `REQ-03` | Bulk upload validation and pending staging | Block invalid data before approval and write valid data into the approval area | `FP-04` | `FE-06`, `FE-07` | `BE-07`, `BE-08`, `BE-09`, `BE-10`, `BE-11` | `DDS-MC-FE-02 Bulk upload page enhancement` | `DDS-MC-BE-03 Bulk upload validation and staging` | `DDS-MC-QA-03 Bulk upload validation regression` | `FE:TBD / BE:TBD / QA:TBD` | `Not Started` |
| `REQ-04` | SSD row-level Add/Edit/Delete/Submit | Support self-service maintenance through the approval flow | `FP-05` | `FE-08`, `FE-09`, `FE-10`, `FE-11` | `BE-12`, `BE-13`, `BE-14`, `BE-15` | `DDS-MC-FE-03 SSD row maintenance and submit UX` | `DDS-MC-BE-04 SSD submit API and conflict control` | `DDS-MC-QA-04 SSD submit regression` | `FE:TBD / BE:TBD / QA:TBD` | `Not Started` |
| `REQ-05` | Approver Dashboard list and details | Allow Approver and Viewer to see pending records, history, and request details | `FP-06` | `FE-12`, `FE-13`, `FE-14` | `BE-16`, `BE-17`, `BE-18` | `DDS-MC-FE-04 Approver dashboard UI` | `DDS-MC-BE-05 Approval dashboard query APIs` | `DDS-MC-QA-05 Dashboard query regression` | `FE:TBD / BE:TBD / QA:TBD` | `Not Started` |
| `REQ-06` | Approve / Reject / Batch / Comments | Support single and batch approval actions with persisted comments | `FP-07` | `FE-15`, `FE-16`, `FE-17` | `BE-19`, `BE-20`, `BE-21` | `DDS-MC-FE-04 Approver dashboard UI` | `DDS-MC-BE-06 Approve reject action APIs` | `DDS-MC-QA-06 Approval action regression` | `FE:TBD / BE:TBD / QA:TBD` | `Not Started` |
| `REQ-07` | Publish, version, history, and audit | After approval, assign the formal version and publish safely: Add starts from `1.0`, Update increments sequentially without time overlap, Delete disables the current record and closes the effective period by default, and all changes remain traceable | `FP-08` | `FE-14`, `FE-18` | `BE-22`, `BE-23`, `BE-24`, `BE-25`, `BE-26`, `BE-27` | `DDS-MC-FE-05 Status and history visibility` | `DDS-MC-BE-07 Publish version history audit` | `DDS-MC-QA-07 Publish and audit regression` | `FE:TBD / BE:TBD / QA:TBD` | `Not Started` |
| `REQ-08` | Help, search, and notification hooks | Fill usability gaps and provide basic operational support | `FP-09` | `FE-19`, `FE-20` | `BE-28`, `BE-29` | `DDS-MC-FE-06 Help and search enhancement` | `DDS-MC-BE-08 Search and notification hook` | `DDS-MC-QA-08 Help/search regression` | `FE:TBD / BE:TBD / QA:TBD` | `Not Started` |
| `REQ-09` | Testing, migration, and rollout readiness | Ensure the change can be released safely and rolled back if needed | `FP-10` | `FE-21` | `BE-30`, `BE-31` | `DDS-MC-FE-07 FE regression support` | `DDS-MC-BE-09 Migration and rollout support` | `DDS-MC-QA-09 E2E UAT and rollout` | `FE:TBD / BE:TBD / QA:TBD` | `Not Started` |

## 7. Frontend Development Details

### 7.1 Auth and Permission

`FE-01` Unified interception for write actions and lazy login entry

- connect all write entry points to a unified login check
- cover `Upload`, `Add`, `Edit`, `Delete`, `Submit`, `Approve`, and `Reject`

`FE-02` Post-login return and action recovery

- return to the original page after login
- restore user context, for example continue upload, continue submit, or continue approval

`FE-03` Tenant-role aware button visibility and disabled states

- anonymous users only get read-only capability
- Requester, Approver, and Viewer permissions are controlled by tenant

### 7.2 Bulk Upload Page

`FE-04` Template download entry and label update

- update the button label to `Download Data Dictionary Template`
- show template version or last updated time

`FE-05` Upload entry and interaction redesign

- file selection, upload button, progress, success and failure messages
- redirect to request or dashboard after successful upload

`FE-06` Upload result and error display

- show request id
- show row-level errors
- show file-level validation failure messages

`FE-07` Post-upload visibility and state feedback

- uploaded records should be visible in the Approver Dashboard
- the Maker should be able to see their own upload result

### 7.3 SSD Data Set Page

`FE-08` Row-level Add / Edit / Delete entry points

- add an `Add` button
- add row-level `Edit` and `Delete`

`FE-09` Row-level edit and add forms

- editable row form
- new row input form

`FE-10` Basic frontend validation

- required field validation
- basic format validation
- prevent obviously invalid submission as early as possible

`FE-11` Submit interaction and Maker comments

- `Submit` button
- comments dialog
- clear edit state and refresh status after successful submit

### 7.4 Approver Dashboard

`FE-12` Dashboard page shell

- `Pending` tab
- `My Requests` tab
- extensible history view entry

`FE-13` List, filter, and status display

- request id, tenant, maker, submit time, status, action type
- support basic filter and search

`FE-14` Request details and field display

- request detail page or drawer
- display business fields, system fields, approval status, and version information

`FE-15` Old vs new diff view

- Update records must show old vs new comparison

`FE-16` Single approve / reject interaction

- approve or reject selected records
- capture checker comments

`FE-17` Batch approve / reject interaction

- support multi-select
- refresh the list after batch actions

`FE-18` History, status, and audit visibility

- users can view the status of their own requests
- show approved, rejected, and pending outcomes where applicable
- the history view must clearly distinguish the current effective version from historical closed versions

### 7.5 Enhancements and Delivery Support

`FE-19` Help content update

- add Maker / Checker process guidance

`FE-20` Search enhancement and unified message handling

- basic search by maker, checker, version, date, and status
- unified handling for 401 / 403 / 409 / 422 responses

`FE-21` Frontend test support and rollout support

- cover key interactions with regression testing
- support SIT / UAT / rollout verification

## 8. Backend Development Details

### 8.1 Auth, Permission, and Role Model

`BE-01` Tenant-level role mapping

- support tenant-level permission checks for Requester, Approver, and Viewer

`BE-02` Extended login response model

- return employee id, display name, and tenant-role information

`BE-03` Unified authorization interception for write APIs

- enable authorization checks on all write endpoints
- distinguish clearly between `401` and `403`

`BE-04` Self-approval guard

- block a Requester from approving their own request

### 8.2 Template and Upload Entry

`BE-05` Template download API and template version management

- provide the updated template with `Dictionary Action`

`BE-06` Upload endpoint and file intake

- accept uploaded files
- extract tenant, domain, and source metadata

### 8.3 Bulk Upload Validation and Staging

`BE-07` File hash and duplicate file detection

- support duplicate file detection

`BE-08` Template structure and file-level validation

- validate template completeness
- validate required columns

`BE-09` Data-level validation

- duplicate primary/composite key detection
- required fields
- special characters
- allowed value ranges
- type and length validation

`BE-10` Bulk upload error model

- return row-level errors
- return file-level errors

`BE-11` Bulk upload pending staging

- create request records
- create approval item records

### 8.4 UI Submit and Conflict Control

`BE-12` UI Submit API

- accept add, edit, and delete change payloads

`BE-13` Old/new snapshot generation

- preserve old and new values for Update records

`BE-14` Convert Delete into soft-delete request

- standardize delete requests as `Dictionary Action = D`

`BE-15` Pending conflict control

- block repeated submission when the same business key already has a pending request

### 8.5 Dashboard Query and Approval APIs

`BE-16` Pending list API

- support basic filtering by tenant, status, date, and similar dimensions

`BE-17` My Requests API

- return requests submitted by the current user and their statuses

`BE-18` Request detail / diff API

- return item-level details
- return old/new diff for Update

`BE-19` Approve API

- single approve
- batch approve

`BE-20` Reject API

- single reject
- batch reject

`BE-21` Comments and request/item status aggregation

- persist maker and checker comments
- aggregate request-level status

### 8.6 Publish, Version, History, and Audit

`BE-22` Add publish logic

- create a formal published record only after approval
- create a new record
- initialize version as `1.0`
- set `Effective From = approval timestamp`
- set `Effective To = null`

`BE-23` Update publish logic

- find the current active version
- set old version `Effective To = approval timestamp`
- create a new version
- increment the version sequentially, for example `1.0 -> 2.0`
- set new version `Effective From = approval timestamp`
- guarantee no overlap between old and new validity windows

`BE-24` Delete publish logic

- implement soft delete / disable according to the raw requirement
- do not create a new version number by default
- update the current active record to `Record Status = D`
- it is recommended to also set `Effective To = approval timestamp`

`BE-25` Transaction control and concurrency protection

- approval and publish actions must complete consistently
- protect:
  - sequential version assignment
  - effective period switching
  - audit log writing
  - concurrent approval scenarios that could cause skipped versions or overlapping periods

`BE-26` Audit log persistence

- store tenant, maker, checker, action, old/new value, and timestamp

`BE-27` Historical version query

- query historical versions by business key
- distinguish current and historical versions
- support future extension to dedicated history tables or partitioning

### 8.7 Enhancements and Delivery Support

`BE-28` Search API enhancement

- support search by maker, checker, version, date, and status

`BE-29` Help / Notification Hook support

- provide support for help content or notification hooks

`BE-30` Data model, migration, and indexing

- approval tables
- audit log
- new fields in the main table
- indexes and unique constraints

`BE-31` Go-live support and rollback preparation

- migration runbook
- rollout support
- rollback readiness

## 9. Recommended Jira Ticket Structure and Tracking

### 9.1 Recommended Epics

| Epic ID | Epic Name | Coverage |
| --- | --- | --- |
| `EPIC-01` | Access and Authorization | `REQ-01` |
| `EPIC-02` | Bulk Upload | `REQ-02`, `REQ-03` |
| `EPIC-03` | SSD Self-Service Maintenance | `REQ-04` |
| `EPIC-04` | Approver Dashboard | `REQ-05`, `REQ-06` |
| `EPIC-05` | Publish, Version, and Audit | `REQ-07` |
| `EPIC-06` | Search, Help, and Notification | `REQ-08` |
| `EPIC-07` | Test, Migration, and Rollout | `REQ-09` |

### 9.2 Recommended Stories

| Suggested Jira ID | Type | Story Name | Suggested Owner | Covered Development Points |
| --- | --- | --- | --- | --- |
| `DDS-MC-FE-01` | FE Story | Lazy login and permission gating | FE | `FE-01`, `FE-02`, `FE-03` |
| `DDS-MC-BE-01` | BE Story | Tenant auth and role service | BE | `BE-01`, `BE-02`, `BE-03`, `BE-04` |
| `DDS-MC-FE-02` | FE Story | Bulk upload page enhancement | FE | `FE-04`, `FE-05`, `FE-06`, `FE-07` |
| `DDS-MC-BE-02` | BE Story | Template API and file intake | BE | `BE-05`, `BE-06` |
| `DDS-MC-BE-03` | BE Story | Bulk upload validation and staging | BE | `BE-07`, `BE-08`, `BE-09`, `BE-10`, `BE-11` |
| `DDS-MC-FE-03` | FE Story | SSD row maintenance and submit UX | FE | `FE-08`, `FE-09`, `FE-10`, `FE-11` |
| `DDS-MC-BE-04` | BE Story | SSD submit API and conflict control | BE | `BE-12`, `BE-13`, `BE-14`, `BE-15` |
| `DDS-MC-FE-04` | FE Story | Approver dashboard UI | FE | `FE-12`, `FE-13`, `FE-14`, `FE-15`, `FE-16`, `FE-17` |
| `DDS-MC-BE-05` | BE Story | Approval dashboard query APIs | BE | `BE-16`, `BE-17`, `BE-18` |
| `DDS-MC-BE-06` | BE Story | Approve reject action APIs | BE | `BE-19`, `BE-20`, `BE-21` |
| `DDS-MC-FE-05` | FE Story | Status and history visibility | FE | `FE-18` |
| `DDS-MC-BE-07` | BE Story | Publish version history audit | BE | `BE-22`, `BE-23`, `BE-24`, `BE-25`, `BE-26`, `BE-27` |
| `DDS-MC-FE-06` | FE Story | Help and search enhancement | FE | `FE-19`, `FE-20` |
| `DDS-MC-BE-08` | BE Story | Search and notification hook | BE | `BE-28`, `BE-29` |
| `DDS-MC-BE-09` | BE Story | Migration and rollout support | BE | `BE-30`, `BE-31` |
| `DDS-MC-QA-01` | QA Story | Auth and role regression | QA | `REQ-01` |
| `DDS-MC-QA-02` | QA Story | Upload and staging regression | QA | `REQ-02`, `REQ-03` |
| `DDS-MC-QA-03` | QA Story | SSD submit and approval regression | QA | `REQ-04`, `REQ-05`, `REQ-06` |
| `DDS-MC-QA-04` | QA Story | Publish audit history regression | QA | `REQ-07` |
| `DDS-MC-QA-05` | QA Story | UAT and rollout verification | QA | `REQ-08`, `REQ-09` |

### 9.3 Jira Tracking Recommendations

- every `REQ-xx` should be covered by at least one FE Story or BE Story
- every `FE-xx` and `BE-xx` development point must be covered by a Story
- add the following fields in Jira:
  - `Req ID`
  - `Feature Point ID`
  - `Owner`
  - `Dependency`
  - `Target Sprint`
  - `Status`
- review the coverage matrix weekly and close any remaining `TBD` Jira gaps

## 10. Delivery Checklist

### 10.1 Frontend Definition of Done

- all write actions are connected to login interception
- page-level permission rendering matches tenant-role rules
- bulk upload, SSD submit, dashboard, diff, and approve/reject interactions work end to end
- key error codes have clear user-facing feedback

### 10.2 Backend Definition of Done

- all write APIs enforce tenant-level permission checks
- bulk upload and UI submit both write into the approval area instead of updating the main table directly
- post-approval main table updates, version switching, and audit logging are completed in a transaction
- history queries and approval queries are supported

### 10.3 QA / UAT Definition of Done

- complete end-to-end regression for auth, upload, submit, approve, reject, publish, and audit
- cover edge cases such as self-approval prevention, duplicate submit prevention, soft delete, sequential version increment, and diff display
- production release can only proceed after UAT sign-off

## 11. Open Items

| Open Item ID | Open Question | Impact Area |
| --- | --- | --- |
| `TBD-01` | Whether `Viewer` must be a tenant-level role | permission model, Dashboard |
| `TBD-02` | Whether `partial approval` is mandatory in phase 1 or only needs architectural compatibility | Dashboard, approval status model |
| `TBD-03` | Whether duplicate file means same name, same hash, or tenant + hash | upload validation |
| `TBD-04` | Whether Maker comments are mandatory | FE Submit, BE validation |
| `TBD-05` | Whether rejected changes should reuse the original request or create a new request | request model, UI experience |
| `TBD-06` | Whether email notification is in scope for phase 1 | notification |
| `TBD-07` | Whether search enhancement and Help updates must go live in phase 1 | scope, planning |
| `TBD-08` | Whether the current main table already supports a versioned key model | data model, migration |
| `TBD-09` | Whether Delete should only disable the current version or also create a dedicated disabled version | versioning strategy, publish logic |
| `TBD-10` | Whether history should be stored in one versioned table or in current + history tables | data model, performance, migration |
