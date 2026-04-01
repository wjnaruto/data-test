# Data Dictionary Service Maker-Checker Development Breakdown

## 1. Document Purpose

This document is based on the requirement screenshots and is intended to:

- summarize the scope of the new Maker-Checker capability for the Data Dictionary Service
- break down backend, frontend, data model, validation, and audit requirements
- provide a task list that can be converted directly into Jira tickets

Notes:

- Current known state: the service mainly supports manual metadata upload and UI display; read operations are generally open without login.
- Core new requirement: add a `maker-requester` and `checker-approver` approval flow for both `bulk upload` and `UI add/edit/delete`.
- Based on your clarification, the login strategy should be: authenticate only when a user performs write or approval actions; keep read-only browsing open where possible.
- This document also includes engineering assumptions for areas that are not fully explicit in the screenshots, and lists open questions at the end.

## 2. Requirement Summary

### 2.1 Business Goals

- introduce a maker-checker governance flow for the Data Dictionary
- support two change entry points:
  - bulk upload through a template file
  - row-level add, edit, and delete actions in the UI
- send all changes to a pending approval area before publishing to the main data set
- enforce AD group based access control at tenant level
- support versioning, history, and audit traceability

### 2.2 Role Definitions

- `Requester / Maker`
  - initiates data changes
  - submits changes through template upload or row-level UI maintenance
  - can view records submitted by themselves and their statuses
- `Approver / Checker`
  - reviews pending changes
  - can approve or reject, including bulk actions
  - cannot approve records submitted by themselves
- `Viewer`
  - can only view submitted requests and statuses
  - cannot approve or reject

### 2.3 Login and Authorization Principles

- read operations remain anonymous by default:
  - dictionary query
  - search results browsing
  - normal page display
- the following actions must trigger login validation:
  - upload template file
  - add record
  - edit record
  - delete record
  - submit changes
  - approve or reject in the approver dashboard
- after successful login, the system should continue the action the user originally attempted, rather than forcing the user to restart the flow manually

## 3. End-to-End Flow Summary

### 3.1 Bulk Upload Flow

1. The maker downloads the template.
2. The maker fills in the template and sets `Dictionary Action` to `A/U/D`.
3. The maker uploads the file.
4. The system checks whether the user is logged in and belongs to the Requester AD Group for the relevant tenant.
5. The system performs file-level and data-level validation.
6. If validation succeeds, the system writes records into the approval staging area with status `Pending`.
7. The approver reviews pending records in the dashboard.
8. The approver approves or rejects by record or by batch and provides comments.
9. If approved, the system publishes the changes to the main table and writes version history and audit logs.
10. If rejected, the records remain in the approval area with status `Rejected` so the maker can review and resubmit.

### 3.2 UI Add / Edit / Delete Flow

1. The user browses the dictionary detail page.
2. When the user clicks `Add`, `Edit`, or `Delete`, the system triggers login validation.
3. After login, the user enters editable mode.
4. The user finishes changes and clicks `Submit`.
5. The system shows a comment dialog so the maker can add remarks.
6. The system copies the changes from the current data set into the approval staging area and sets status to `Pending`.
7. The approver reviews the changes in the dashboard and decides to approve or reject.
8. If approved:
   - `A`: create a new record
   - `U`: close the old version and create a new version
   - `D`: apply soft delete and set `Record Status` to `D`
9. If rejected, the main table remains unchanged and the approval record is set to `Rejected`.

### 3.3 Approver Dashboard Flow

1. An approver or viewer opens the dashboard.
2. The system determines the user role:
   - approver: can review, compare, approve, and reject in bulk
   - viewer: view only
3. The default tab is `Pending`.
4. The `My Requests` tab shows records submitted by the current user and their history.
5. For `Update` records, the dashboard should display old and new values side by side.
6. Approver actions must capture comments and persist them.

## 4. Recommended Data Architecture

The screenshots mention a new `approval table`. From an implementation perspective, a single table is likely too limited. A more maintainable design is to split the model into request header, approval item, and audit log, especially if bulk submission, partial approval, comments, and history queries are required.

### 4.1 Recommended Table Design

#### A. `approval_request`

Represents one submission request, for example one bulk upload or one UI submit action.

Suggested fields:

- `request_id`
- `tenant`
- `domain`
- `source_type`: `UPLOAD` / `UI`
- `submitted_by`
- `submitted_at`
- `maker_comment`
- `request_status`: `PENDING / PARTIALLY_APPROVED / APPROVED / REJECTED`
- `reviewed_by`
- `reviewed_at`
- `checker_comment`
- `source_file_name`
- `source_file_hash`

#### B. `approval_item`

Represents one pending record within a request.

Suggested fields:

- `approval_item_id`
- `request_id`
- `entity_type`: for example dataset / attribute / table
- `business_key` or `primary_key_snapshot`
- `dictionary_action`: `A / U / D`
- `approval_status`: `P / A / R`
- `record_status`: `A / D`
- `requester_id`
- `approver_id`
- `requester_timestamp`
- `approver_timestamp`
- `version`
- `effective_from`
- `effective_to`
- `old_value_json`
- `new_value_json`
- `validation_errors_json`
- `maker_comment`
- `checker_comment`

#### C. `dictionary_audit_log`

Stores the final audit trail.

Suggested fields:

- `audit_id`
- `request_id`
- `approval_item_id`
- `tenant`
- `entity_type`
- `business_key`
- `action_type`
- `maker_id`
- `checker_id`
- `changed_at`
- `old_value_json`
- `new_value_json`
- `version`

#### D. `tenant_role_mapping` or configuration-based mapping

Maintains the relationship between tenants and AD groups.

Suggested fields:

- `tenant`
- `domain`
- `requester_group_cn`
- `approver_group_cn`
- `viewer_group_cn` if needed
- `environment`

### 4.2 Additional Main Table Fields

Based on the screenshots, the main table or version table should support at least:

- `Requester_ID`
- `Approver_ID`
- `Requester_Timestamp`
- `Approver_Timestamp`
- `Version`
- `Dictionary_Action`
- `Approval_Status`
- `Record_Status`
- `Effective_From`
- `Effective_To`

### 4.3 Recommended Implementation Principles

- keep only published and effective versions in the main table
- store pending data only in approval tables, not directly in the main table
- for `Update`, close the old version and create a new version after approval
- for `Delete`, use soft delete rather than physical delete
- version numbers must always increase and must not be reused or skipped

## 5. Detailed Backend Functional Breakdown

## 5.1 Authentication and Authorization

### BE-01 Login Session Validation

- reuse the existing LDAP/JWT login mechanism so the frontend can trigger login before write actions
- support both Cookie and JWT based session identification
- add an API, or extend `/auth/me`, so the frontend can know whether the current user has write access for the current tenant
- return explicit `401` and `403` responses so the frontend can trigger login or show an access error correctly

### BE-02 Tenant-Level AD Group Authorization

- support requester, approver, and viewer permissions by tenant
- permission checks must not be global-only; they must be tenant-specific
- the same user may have different roles across different tenants
- the backend must validate:
  - the uploader belongs to the requester group of the relevant tenant
  - the approver belongs to the approver group of the relevant tenant
  - requester and approver are not the same employee id

### BE-03 Permission Response Model

- after login, return:
  - user id
  - employee id
  - display name
  - accessible tenant list
  - role list for each tenant
- this is needed so the frontend can control button visibility and dashboard permissions

## 5.2 Template and Bulk Upload

### BE-04 Template Download Capability

- update the template download API
- add `Dictionary Action` into the template
- make the template version traceable so the frontend and users do not accidentally use outdated templates

### BE-05 Bulk Upload Parsing and Persistence

- accept uploaded files
- parse tenant, domain, entities, and row-level data from the file
- calculate file hash for duplicate checking
- transform parsed rows into `approval_request + approval_item`
- persist source file name, uploader, and upload time

### BE-06 Bulk Upload Validation

- duplicate file validation
- template structure validation
- tenant/domain validity check
- `Dictionary Action` value validation, only allowing `A/U/D`
- data-level validation:
  - duplicate primary key or composite key
  - mandatory field not null
  - special character validation
  - allowed value range validation
  - data type and length validation
- if validation fails, return row-level errors for frontend display

### BE-07 Bulk Upload Submission Result

- write successful uploads into `Pending`
- return request id, success count, failure count, and error details
- optionally trigger notification to approvers

## 5.3 UI Row-Level Change and Submission

### BE-08 Row-Level Add / Edit / Delete Staging

- allow the UI to submit one or more added, updated, or deleted records together
- do not update the main table directly; always create approval records first
- for `Edit`, persist both old and new values
- for `Delete`, convert to `Dictionary Action = D`

### BE-09 Submit API

- support multiple record changes in one submit action
- support maker comments
- create `approval_request`
- create multiple `approval_item` records
- set all statuses to `Pending`

### BE-10 De-duplication and Concurrency Control

- prevent duplicate submissions when a pending change already exists for the same business key
- prevent version conflicts caused by multiple approvers reviewing the same data
- use transaction control for version increment and effective date updates

## 5.4 Approver Dashboard Backend Capability

### BE-11 Approval List Query

- query `Pending` requests
- query `My Requests`
- query historical requests
- support filtering by tenant, status, maker, checker, date, and entity type

### BE-12 Detail and Difference View

- return all items within one request
- return old and new diffs for `Update`
- return action type, primary key, comments, and source for `Add/Delete`

### BE-13 Approve / Reject APIs

- support single approval
- support bulk approval
- support single rejection
- support bulk rejection
- require checker comments for approval and rejection

### BE-14 Partial Approval Support

- if a request can be partially approved and partially rejected, the design must include:
  - item-level status
  - request-level aggregated status
- if the product decides not to support partial approval, the flow can be simplified to full request approve or reject
- the screenshot mentions `approve fully or partially`, so item-level design is recommended to avoid rework later

## 5.5 Publish Logic After Approval

### BE-15 `Add` Publish Logic

- create a new record in the main table
- initialize the version as `1.0`
- set `Record Status = A`
- set `Effective From = current timestamp`
- set `Effective To = null`

### BE-16 `Update` Publish Logic

- find the current active version
- update the old version `Effective To` to current timestamp
- create a new version record
- increment the version number, for example `1.0 -> 2.0`
- set new version `Effective From = current timestamp`
- set new version `Effective To = null`

### BE-17 `Delete` Publish Logic

- do not physically delete records
- set the current effective record in the main table to `Record Status = D`
- close the effective period of the current version
- keep full traceability in the approval tables and audit log

## 5.6 Audit, History, and Search

### BE-18 Audit Logging

- write audit logs after approval
- audit content should include at least:
  - tenant
  - maker
  - checker
  - action type
  - old value
  - new value
  - change time
  - version

### BE-19 Historical Version Query

- support query of all historical versions by business key
- support viewing `effective from / to`
- distinguish the current effective version from closed historical versions

### BE-20 Search Enhancement

- support searching by maker, checker, version, approval status, and date
- this can be delivered as a phase 2 feature

## 5.7 Notification and Help

### BE-21 Notification Capability

- notify approver after successful upload
- notify maker after rejection
- notify maker after approval
- if email is out of scope for phase 1, at least keep an event hook or interface for future notification integration

### BE-22 Help Content Support

- provide maker/checker process content for the frontend help section, or implement it as static frontend content

## 6. Detailed Frontend Functional Breakdown

## 6.1 Login Trigger and Page Behavior

### FE-01 Lazy Login Mechanism

- do not force login at initial page load
- when a user clicks the following buttons, trigger login validation:
  - Upload
  - Add
  - Edit
  - Delete
  - Submit
  - Approve
  - Reject
- if the user is not logged in:
  - show a login dialog or redirect to a login page
  - after successful login, return to the original page
  - restore the original action context automatically

### FE-02 Permission-Based UI State

- anonymous users only get read-only capability
- after login, show controls based on role:
  - requester sees upload/add/edit/delete/submit
  - approver sees approve/reject
  - viewer can only view
- if the user does not have permission for the current tenant, hide or disable the buttons

## 6.2 Bulk Upload Page

### FE-03 UI Labels and Entry Updates

- update button labels based on the requirement:
  - `Download Data Dictionary Template`
  - `Upload Data Dictionary Template`

### FE-04 Template Download

- provide a template download entry
- show template version or last updated time

### FE-05 File Upload Interaction

- upload after file selection
- show upload progress and success or failure feedback
- show file-level and row-level errors
- after success, navigate to the relevant request detail or dashboard

### FE-06 Upload Result Feedback

- show request id on success
- show row-level errors on failure
- optionally show a message that approvers have been notified

## 6.3 SSD Data Set Page Changes

### FE-07 Row-Level Action Entry

- add `Edit` and `Delete` to each row
- add an `Add` button to the page
- support basic frontend validation for new and edited rows

### FE-08 New Field Display

- show the following fields in the data set page or a detail panel:
  - Dictionary Action
  - Approval Status
  - Version
  - Requester
  - Approver
  - Requester Timestamp
  - Approver Timestamp
- system-generated fields should preferably be shown in a details or history section to avoid an overly wide main table

### FE-09 Submit Interaction

- allow users to make multiple changes and submit them together
- show a comments dialog on submit
- clear frontend edit state after successful submission
- refresh the page and show that the records have entered `Pending`

### FE-10 Duplicate Submission and Conflict Message

- if the backend returns a message such as "pending request already exists", the frontend should show it clearly
- guide the user to `My Requests` instead of letting the user submit repeatedly

## 6.4 Approver Dashboard

### FE-11 Dashboard Page Structure

- at minimum include:
  - `Pending` tab
  - `My Requests` tab
- optional extensions:
  - `All`
  - `Approved`
  - `Rejected`

### FE-12 List and Filter

- show basic request information:
  - request id
  - tenant
  - maker
  - submit time
  - status
  - action type
- support filter and search

### FE-13 Details and Diff Display

- click a request to view all changed items
- show old vs new comparison for `Update`
- show action type and key fields for `Add/Delete`

### FE-14 Approval Actions

- support single approve/reject
- support multi-select bulk approve/reject
- show a comment dialog during approval
- refresh the list after the operation succeeds

### FE-15 Viewer Mode

- viewers can enter the dashboard but can only view
- do not render approve or reject buttons for viewers

## 6.5 Search, Help, and Status Feedback

### FE-16 Search Enhancement

- support searching by maker, checker, version, status, and date

### FE-17 Help Page Update

- add maker/checker process guidance
- add usage instructions for bulk upload and UI submit
- add guidance for what to do after rejection

### FE-18 Unified User Feedback

- login expired message
- upload success/failure message
- submit success/failure message
- approval success/failure message

## 7. Core Business Rules

### 7.1 Approval Status Rules

- `Pending`: submitted by maker and waiting for review
- `Approved`: approved by checker
- `Rejected`: rejected by checker

### 7.2 Record Status Rules

- `A`: Active
- `D`: Disabled

### 7.3 Action Rules

- `A`: Add
- `U`: Update
- `D`: Delete or Disable

### 7.4 Approval Restriction Rules

- the checker cannot approve their own request
- even if a user has both maker and approver roles, self-approval must still be blocked
- only one active version can exist for a business record at any given time
- `effective_to` must be earlier than or equal to the new version `effective_from`

## 8. Recommended API List

The following is a suggested API list to support frontend and backend implementation. It does not have to be adopted exactly as-is:

- `POST /auth/login`
- `GET /auth/me`
- `GET /auth/permissions?tenant=...`
- `GET /dictionary/templates/latest`
- `POST /dictionary/uploads`
- `POST /dictionary/changes/submit`
- `GET /approvals/pending`
- `GET /approvals/my-requests`
- `GET /approvals/{request_id}`
- `POST /approvals/{request_id}/approve`
- `POST /approvals/{request_id}/reject`
- `POST /approvals/items/bulk-approve`
- `POST /approvals/items/bulk-reject`
- `GET /dictionary/history/{business_key}`
- `GET /dictionary/audit`

## 9. Jira Breakdown Recommendation

It is recommended to split work using `Epic -> Story`, rather than putting DB, API, frontend, and approval logic into a single ticket.

### Epic 1: Permission and Login Foundation

- `BE Story`: add tenant-level AD group mapping and authorization
- `BE Story`: extend login response with tenant-role model
- `FE Story`: implement lazy login and post-login return flow for write actions
- `FE Story`: implement permission-based button visibility and disabled states

### Epic 2: Data Model and Migration

- `BE Story`: design approval request/item/audit log tables and migration
- `BE Story`: add version and status fields to the main table
- `BE Story`: add historical version query foundation

### Epic 3: Bulk Upload

- `BE Story`: update template download API and template fields
- `BE Story`: implement upload, parsing, validation, and pending staging
- `BE Story`: implement duplicate file detection and row-level error response
- `FE Story`: update the bulk upload page
- `FE Story`: display upload results and errors

### Epic 4: UI Self-Service Submit

- `BE Story`: implement Add/Edit/Delete staging and submit API
- `BE Story`: store maker comments and implement concurrency control
- `FE Story`: add row-level add/edit/delete capability to SSD pages
- `FE Story`: implement submit dialog and pending status feedback

### Epic 5: Approver Dashboard

- `BE Story`: implement pending, my requests, and history query APIs
- `BE Story`: implement diff detail API
- `BE Story`: implement approve/reject single and bulk APIs
- `FE Story`: build dashboard list and tabs
- `FE Story`: build request detail and diff view
- `FE Story`: build bulk approval and comment dialog interactions

### Epic 6: Publish, Version, and Audit

- `BE Story`: implement publish logic for add/update/delete after approval
- `BE Story`: implement version increment and effective from/to maintenance
- `BE Story`: persist audit log
- `BE Story`: implement self-approval prevention and transaction consistency

### Epic 7: Experience Enhancements and Additional Features

- `FE Story`: add My Requests history and status tracking
- `FE Story`: update Help content
- `BE Story`: add notification hooks or email notification
- `FE/BE Story`: implement search enhancement as a nice-to-have

## 10. Recommended Delivery Sequence

1. first complete the permission model, DB design, and approval table migration
2. then complete the backend bulk upload end-to-end flow, because it is the clearest main path
3. then implement UI row-level add/edit/delete submit
4. then implement the approver dashboard
5. finally add search, help, notification, and history optimizations

## 11. Open Questions

These items should be clarified before Jira creation to avoid incorrect ticket breakdown:

- should `Viewer` also be a tenant-level AD group, or should any logged-in user be able to view
- should the approver dashboard allow anonymous viewing
- does `partial approve` really mean item-level approval within one request, or is it only descriptive wording
- how is `duplicate file` defined for bulk upload:
  - same file name
  - same hash
  - same tenant plus same hash
- after rejection, should the maker resubmit on the original request or create a new request
- is notification in scope for this phase:
  - in-app message
  - email
  - or only visibility in the pending list
- should the template expose system fields such as `Approval Status / Version / Requester / Approver`, or only expose `Dictionary Action`
- does the current main table already have a version key; if not, the versioned storage design must be clarified
- are search enhancement and Help update mandatory for phase 1, or phase 2 nice-to-have items

## 12. Suggested Jira Story Titles

- `BE | Add tenant-level requester/approver authorization for data dictionary`
- `BE | Create approval request and approval item tables for maker-checker flow`
- `BE | Implement bulk upload validation and pending staging`
- `BE | Implement approval publish logic for add/update/delete actions`
- `BE | Add audit log and version history persistence`
- `FE | Add lazy login flow for write actions`
- `FE | Update data dictionary bulk upload page for maker flow`
- `FE | Add row-level add/edit/delete and submit flow to SSD pages`
- `FE | Build approver dashboard with pending and my requests tabs`
- `FE | Add approval diff view and batch approve/reject interactions`

## 13. Full Task Breakdown List

This section further breaks the Epic and Story level scope down into executable tasks. Recommended Jira hierarchy:

- `Epic -> Story -> Task -> Sub-task`
- if your Jira setup is flatter, you can also use:
- `Epic -> Story -> Sub-task`

Recommended fields:

- `Task ID`
- `Area`
- `Task`
- `Suggested Owner`
- `Depends On`
- `Deliverable`

### 13.1 Analysis / Design / Alignment

- `TD-01 | Analysis | Hold a requirement clarification session to confirm phase 1 scope and out-of-scope items such as viewer, notification, partial approve, search enhancement, and help update | Owner: BA/PO + Tech Lead | Depends On: none | Deliverable: scope baseline`
- `TD-02 | Analysis | Confirm the login strategy: anonymous read, login for write actions, login for approval actions, and post-login return behavior | Owner: BA/PO + FE Lead + BE Lead | Depends On: TD-01 | Deliverable: auth interaction decision`
- `TD-03 | Analysis | Confirm the source of tenant to AD group mapping: config file, database table, or external directory service | Owner: Architect + Security + BE Lead | Depends On: TD-01 | Deliverable: tenant-role mapping approach`
- `TD-04 | Analysis | Confirm approval granularity: full request approval only, or item-level partial approval | Owner: BA/PO + Tech Lead | Depends On: TD-01 | Deliverable: approval granularity decision`
- `TD-05 | Analysis | Confirm the duplicate file rule for bulk upload: file name, hash, tenant + hash, or another combination | Owner: BA/PO + BE Lead | Depends On: TD-01 | Deliverable: duplicate check rule`
- `TD-06 | Analysis | Confirm the maker resubmission model after rejection: new request or reuse existing request | Owner: BA/PO + BE Lead + FE Lead | Depends On: TD-01 | Deliverable: resubmission rule`
- `TD-07 | Design | Produce a maker-checker data flow and status flow design | Owner: Solution Architect | Depends On: TD-02, TD-04, TD-06 | Deliverable: solution design`
- `TD-08 | Design | Define versioning rules: initial version, increment on update, delete behavior, and effective from/to rules | Owner: Architect + BE Lead | Depends On: TD-07 | Deliverable: versioning design`
- `TD-09 | Design | Define audit scope: when to log, which fields to capture, and how to store old/new values | Owner: Architect + Audit/Control SME + BE Lead | Depends On: TD-07 | Deliverable: audit design`
- `TD-10 | Design | Define the API contract draft and error code conventions covering login, upload, submit, approve, conflict, and validation failure | Owner: BE Lead + FE Lead | Depends On: TD-07 | Deliverable: API contract draft`

### 13.2 Data Model / Migration

- `TD-11 | DB | Design the approval_request table structure | Owner: BE/DB Engineer | Depends On: TD-07 | Deliverable: schema draft`
- `TD-12 | DB | Design the approval_item table structure including old_value/new_value, status, comment, and version fields | Owner: BE/DB Engineer | Depends On: TD-07, TD-08 | Deliverable: schema draft`
- `TD-13 | DB | Design the dictionary_audit_log table structure | Owner: BE/DB Engineer | Depends On: TD-09 | Deliverable: schema draft`
- `TD-14 | DB | Design the tenant_role_mapping table or an equivalent configuration structure | Owner: BE/DB Engineer | Depends On: TD-03 | Deliverable: mapping schema`
- `TD-15 | DB | Assess main table or version table changes needed to add Requester/Approver/Version/Status/Effective fields | Owner: BE/DB Engineer | Depends On: TD-08 | Deliverable: main table change design`
- `TD-16 | DB | Design unique constraints and indexes for pending conflict checks, request queries, my requests queries, and history queries | Owner: BE/DB Engineer | Depends On: TD-11, TD-12, TD-15 | Deliverable: index strategy`
- `TD-17 | DB | Implement Alembic migration scripts | Owner: BE Engineer | Depends On: TD-11, TD-12, TD-13, TD-14, TD-15, TD-16 | Deliverable: migration scripts`
- `TD-18 | DB | Prepare initialization or backfill scripts for tenant-role mapping and main table default values | Owner: BE Engineer | Depends On: TD-17 | Deliverable: seed/backfill scripts`
- `TD-19 | DB | Review migration rollback approach and data compatibility risks | Owner: BE Lead + DBA | Depends On: TD-17 | Deliverable: migration runbook notes`

### 13.3 Backend Auth / Authorization

- `TD-20 | BE | Extend login response model to include employee id, display name, and tenant-role information | Owner: BE Engineer | Depends On: TD-03, TD-10 | Deliverable: updated auth response`
- `TD-21 | BE | Implement tenant-level requester/approver/viewer authorization service | Owner: BE Engineer | Depends On: TD-03, TD-14 | Deliverable: authorization service`
- `TD-22 | BE | Add a common authorization dependency or middleware for write APIs and distinguish 401 from 403 | Owner: BE Engineer | Depends On: TD-20, TD-21 | Deliverable: protected write endpoints`
- `TD-23 | BE | Implement self-approval validation to prevent a maker from approving their own request | Owner: BE Engineer | Depends On: TD-21 | Deliverable: approval guard`
- `TD-24 | BE | Provide a permission query API or enhance \`/auth/me\` so the frontend can control button visibility and page access | Owner: BE Engineer | Depends On: TD-20, TD-21 | Deliverable: FE-consumable auth API`

### 13.4 Backend Bulk Upload

- `TD-25 | BE | Update the template download API and template file to include Dictionary Action | Owner: BE Engineer | Depends On: TD-10 | Deliverable: template endpoint + template file`
- `TD-26 | BE | Implement file upload handling, parsing, and tenant/domain identification | Owner: BE Engineer | Depends On: TD-25 | Deliverable: upload parser`
- `TD-27 | BE | Implement duplicate file validation and template structure validation | Owner: BE Engineer | Depends On: TD-05, TD-26 | Deliverable: upload validation layer`
- `TD-28 | BE | Implement data-level validation: duplicate keys, required fields, enums, special characters, and type/length checks | Owner: BE Engineer | Depends On: TD-26 | Deliverable: row validation layer`
- `TD-29 | BE | Persist upload results into approval_request and approval_item with Pending status | Owner: BE Engineer | Depends On: TD-11, TD-12, TD-26, TD-27, TD-28 | Deliverable: staging persistence`
- `TD-30 | BE | Design the upload error response model to support row-level error display | Owner: BE Engineer | Depends On: TD-28, TD-29 | Deliverable: error response contract`
- `TD-31 | BE | Add upload permission validation so only requesters of the relevant tenant can upload | Owner: BE Engineer | Depends On: TD-21, TD-26 | Deliverable: secured upload endpoint`

### 13.5 Backend UI Submit / Staging

- `TD-32 | BE | Design the UI add/edit/delete submission payload to support multi-record submit | Owner: BE Lead + FE Lead | Depends On: TD-10 | Deliverable: submit API contract`
- `TD-33 | BE | Implement the UI submit API to convert add/edit/delete into approval items | Owner: BE Engineer | Depends On: TD-12, TD-32 | Deliverable: submit API`
- `TD-34 | BE | Store old_value and new_value snapshots for Edit actions | Owner: BE Engineer | Depends On: TD-33 | Deliverable: diff-ready staging data`
- `TD-35 | BE | Convert Delete actions into soft-delete requests with Dictionary Action = D | Owner: BE Engineer | Depends On: TD-33 | Deliverable: delete staging logic`
- `TD-36 | BE | Add conflict validation to block submission when a Pending request already exists for the same business key | Owner: BE Engineer | Depends On: TD-16, TD-33 | Deliverable: pending conflict protection`
- `TD-37 | BE | Persist maker comments at request level or item level | Owner: BE Engineer | Depends On: TD-33 | Deliverable: comment persistence`

### 13.6 Backend Approver Dashboard / Review

- `TD-38 | BE | Implement Pending requests list API | Owner: BE Engineer | Depends On: TD-11, TD-12 | Deliverable: pending API`
- `TD-39 | BE | Implement My Requests list API | Owner: BE Engineer | Depends On: TD-11, TD-12 | Deliverable: my requests API`
- `TD-40 | BE | Implement request detail API returning item details and comments | Owner: BE Engineer | Depends On: TD-38, TD-39 | Deliverable: approval detail API`
- `TD-41 | BE | Implement old vs new diff assembly for Update records | Owner: BE Engineer | Depends On: TD-34, TD-40 | Deliverable: diff response model`
- `TD-42 | BE | Implement approve APIs for single and bulk actions | Owner: BE Engineer | Depends On: TD-04, TD-23, TD-40 | Deliverable: approve API`
- `TD-43 | BE | Implement reject APIs for single and bulk actions and require checker comments | Owner: BE Engineer | Depends On: TD-04, TD-23, TD-40 | Deliverable: reject API`
- `TD-44 | BE | Implement request-level aggregated status calculation: Pending, Partially Approved, Approved, Rejected | Owner: BE Engineer | Depends On: TD-04, TD-42, TD-43 | Deliverable: request status aggregation`

### 13.7 Backend Publish / Version / Audit

- `TD-45 | BE | Implement Add publish logic after approval to create the first active version | Owner: BE Engineer | Depends On: TD-15, TD-42 | Deliverable: add publish flow`
- `TD-46 | BE | Implement Update publish logic after approval to close the old version and create a new version | Owner: BE Engineer | Depends On: TD-08, TD-15, TD-42 | Deliverable: update publish flow`
- `TD-47 | BE | Implement Delete publish logic after approval to soft-delete and close the effective period | Owner: BE Engineer | Depends On: TD-08, TD-15, TD-42 | Deliverable: delete publish flow`
- `TD-48 | BE | Add transaction control and concurrency protection to publish logic to prevent duplicate approval and version conflicts | Owner: BE Engineer | Depends On: TD-45, TD-46, TD-47 | Deliverable: transactional consistency`
- `TD-49 | BE | Implement audit log persistence | Owner: BE Engineer | Depends On: TD-13, TD-45, TD-46, TD-47 | Deliverable: audit persistence`
- `TD-50 | BE | Implement history version query API | Owner: BE Engineer | Depends On: TD-15, TD-46, TD-47 | Deliverable: history API`

### 13.8 Frontend Auth / Common UX

- `TD-51 | FE | Identify all current write entry points and connect them to a unified lazy login guard | Owner: FE Engineer | Depends On: TD-02, TD-24 | Deliverable: guarded UI actions`
- `TD-52 | FE | Implement login dialog or redirect and support return to the current page after login | Owner: FE Engineer | Depends On: TD-51 | Deliverable: login recovery flow`
- `TD-53 | FE | Restore interrupted write actions after login, such as continuing upload, reopening edit modal, or continuing submit | Owner: FE Engineer | Depends On: TD-52 | Deliverable: action resume logic`
- `TD-54 | FE | Control Upload/Add/Edit/Delete/Approve/Reject button visibility and disable state based on permission model | Owner: FE Engineer | Depends On: TD-24, TD-51 | Deliverable: role-based UI control`
- `TD-55 | FE | Implement unified handling for 401/403/409/422 messages | Owner: FE Engineer | Depends On: TD-10, TD-54 | Deliverable: global error handling`

### 13.9 Frontend Bulk Upload

- `TD-56 | FE | Update bulk upload page wording and entry layout | Owner: FE Engineer | Depends On: TD-25 | Deliverable: updated upload page`
- `TD-57 | FE | Integrate the template download API and show template version or updated time | Owner: FE Engineer | Depends On: TD-25 | Deliverable: template download UI`
- `TD-58 | FE | Integrate the upload API with file selection, submit, progress, and success/failure feedback | Owner: FE Engineer | Depends On: TD-26, TD-30, TD-31 | Deliverable: upload interaction`
- `TD-59 | FE | Display row-level errors and validation summary | Owner: FE Engineer | Depends On: TD-30, TD-58 | Deliverable: upload error panel`
- `TD-60 | FE | Redirect to the corresponding request or dashboard after successful upload | Owner: FE Engineer | Depends On: TD-29, TD-58 | Deliverable: post-upload navigation`

### 13.10 Frontend SSD Data Set Page

- `TD-61 | FE | Add Add/Edit/Delete action entry points to the SSD page | Owner: FE Engineer | Depends On: TD-54 | Deliverable: row action UI`
- `TD-62 | FE | Implement row-level edit forms and add forms | Owner: FE Engineer | Depends On: TD-61 | Deliverable: edit/add forms`
- `TD-63 | FE | Add basic frontend validation to reduce invalid submissions | Owner: FE Engineer | Depends On: TD-62 | Deliverable: client validation`
- `TD-64 | FE | Implement Submit button and comments dialog | Owner: FE Engineer | Depends On: TD-32, TD-37, TD-62 | Deliverable: submit interaction`
- `TD-65 | FE | Refresh UI state after successful submit and show that records are now Pending | Owner: FE Engineer | Depends On: TD-33, TD-64 | Deliverable: pending status feedback`
- `TD-66 | FE | Display system fields, or show Version, Approval Status, Requester, Approver, and Timestamp in a detail area | Owner: FE Engineer | Depends On: TD-15, TD-65 | Deliverable: system metadata view`
- `TD-67 | FE | Handle the "Pending request already exists" conflict and guide users to My Requests | Owner: FE Engineer | Depends On: TD-36, TD-65 | Deliverable: conflict UX`

### 13.11 Frontend Approver Dashboard

- `TD-68 | FE | Implement dashboard shell and tabs: Pending and My Requests | Owner: FE Engineer | Depends On: TD-38, TD-39 | Deliverable: dashboard shell`
- `TD-69 | FE | Implement Pending list, pagination, filtering, and status display | Owner: FE Engineer | Depends On: TD-38, TD-68 | Deliverable: pending list UI`
- `TD-70 | FE | Implement My Requests list and historical status viewing | Owner: FE Engineer | Depends On: TD-39, TD-68 | Deliverable: my requests UI`
- `TD-71 | FE | Implement request detail drawer or page showing item details and comments | Owner: FE Engineer | Depends On: TD-40, TD-68 | Deliverable: approval detail UI`
- `TD-72 | FE | Implement old vs new diff view | Owner: FE Engineer | Depends On: TD-41, TD-71 | Deliverable: diff UI`
- `TD-73 | FE | Implement single approve/reject actions and comments dialog | Owner: FE Engineer | Depends On: TD-42, TD-43, TD-71 | Deliverable: single review action UI`
- `TD-74 | FE | Implement bulk approve/reject actions | Owner: FE Engineer | Depends On: TD-42, TD-43, TD-69 | Deliverable: bulk review UI`
- `TD-75 | FE | Implement viewer mode with view-only access | Owner: FE Engineer | Depends On: TD-21, TD-68 | Deliverable: viewer-safe dashboard`

### 13.12 Notification / Help / Search Enhancements

- `TD-76 | BE | Design and implement approval result notification hooks, at minimum with an interface or event placeholder | Owner: BE Engineer | Depends On: TD-42, TD-43 | Deliverable: notification hook`
- `TD-77 | FE | Update Help content with maker/checker process guidance | Owner: FE Engineer | Depends On: TD-01 | Deliverable: help content update`
- `TD-78 | BE | If included in phase 1, implement enhanced search APIs for maker/checker/version/date/status | Owner: BE Engineer | Depends On: TD-50 | Deliverable: search API enhancement`
- `TD-79 | FE | If included in phase 1, implement advanced search UI | Owner: FE Engineer | Depends On: TD-78 | Deliverable: search filter UI`

### 13.13 Testing / QA / UAT

- `TD-80 | QA | Write the test scenario matrix covering bulk upload, UI submit, approve, reject, history, audit, and permission boundary cases | Owner: QA Lead | Depends On: TD-10 | Deliverable: QA test matrix`
- `TD-81 | BE | Add unit tests for auth and authorization | Owner: BE Engineer | Depends On: TD-20, TD-21, TD-22, TD-23 | Deliverable: unit tests`
- `TD-82 | BE | Add unit tests for bulk upload parsing and validation | Owner: BE Engineer | Depends On: TD-26, TD-27, TD-28, TD-29 | Deliverable: unit tests`
- `TD-83 | BE | Add unit tests for publish/version/audit flows | Owner: BE Engineer | Depends On: TD-45, TD-46, TD-47, TD-49, TD-50 | Deliverable: unit tests`
- `TD-84 | BE | Add API and integration tests covering the full chain of submit -> approve/reject -> publish | Owner: BE Engineer | Depends On: TD-33, TD-42, TD-43, TD-45, TD-46, TD-47 | Deliverable: integration tests`
- `TD-85 | FE | Add frontend interaction tests covering lazy login, upload, submit, dashboard, and diff | Owner: FE Engineer | Depends On: TD-52, TD-58, TD-64, TD-72, TD-74 | Deliverable: FE tests`
- `TD-86 | QA | Execute SIT/UAT using real tenant-role samples to validate access boundaries | Owner: QA + Business UAT | Depends On: TD-81, TD-82, TD-83, TD-84, TD-85 | Deliverable: UAT sign-off`

### 13.14 Deployment / Release / Rollout

- `TD-87 | DevOps/BE | Prepare configuration and secrets checklist, for example AD group mapping, template version, and feature flags | Owner: DevOps + BE Lead | Depends On: TD-03, TD-25 | Deliverable: config checklist`
- `TD-88 | DevOps/BE | Prepare DB migration execution plan and rollback plan | Owner: DevOps + DBA + BE Lead | Depends On: TD-17, TD-19 | Deliverable: migration runbook`
- `TD-89 | FE/BE | Evaluate whether feature flags should be used to enable maker-checker gradually by tenant | Owner: FE Lead + BE Lead | Depends On: TD-01, TD-87 | Deliverable: rollout strategy`
- `TD-90 | DevOps | Deploy to SIT/UAT/Prod and run smoke tests | Owner: DevOps + QA | Depends On: TD-86, TD-88, TD-89 | Deliverable: environment rollout`
- `TD-91 | BA/PO + Tech Lead | Run a go-live checklist review to confirm monitoring, support contacts, rollback contacts, and known limitations | Owner: PO + Tech Lead | Depends On: TD-90 | Deliverable: go-live approval`

### 13.15 Recommended Jira Ticketing Approach

If you want to control ticket count, do not create all 90+ items above as Stories. A more practical approach is:

- `Epic`: use the section 9 breakdown
- `Story`: split by capability module, for example `Bulk Upload Backend` or `Approver Dashboard Frontend`
- `Task/Sub-task`: use the `TD-xx` items in this section

Recommended minimum executable split:

- keep each backend Story within `3-6` tasks
- keep each frontend Story within `3-5` tasks
- keep DB migration as a standalone Story rather than mixing it into business logic Stories
- keep testing and UAT as standalone Story or task rather than burying them inside development tickets
- keep deployment and rollout as standalone tasks so release preparation has clear ownership
