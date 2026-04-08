# Data Dictionary Service Maker-Checker ER Relationships

## 1. Purpose

This page explains the target entity relationships for the Data Dictionary Service after the Maker-Checker enhancement.

It is intended for:

- frontend developers
- backend developers
- reviewers
- DBAs
- QA engineers

This page clarifies:

- which tables are master data tables
- which tables are current published tables
- which tables are pending approval tables
- which tables are history tables
- which relationships are physical foreign keys
- which relationships are logical associations only

Related design documents:

- [data_dictionary_maker_checker_target_data_model.md](./data_dictionary_maker_checker_target_data_model.md)
- [data_dictionary_maker_checker_target_data_model_ddl_draft.sql](./data_dictionary_maker_checker_target_data_model_ddl_draft.sql)
- [data_dictionary_maker_checker_alembic_migration_checklist.md](./data_dictionary_maker_checker_alembic_migration_checklist.md)

Naming note:

- physical table `table_entity` is the business `dataset`
- physical table `attribute_entity` represents fields under a dataset

## 2. Entity Inventory

| Entity | Layer | Primary Key | Role | Notes |
| --- | --- | --- | --- | --- |
| `domain_entity` | master | `id` | domain master data | existing table |
| `tenant_entity` | master | `id` | tenant master data | existing table |
| `table_entity` | current | `id` | current published dataset | existing table; business meaning = dataset |
| `attribute_entity` | current | `id` | current published attribute | existing table |
| `approval_request` | workflow | `request_id` | request header for one maker submission | new table |
| `tenant_role_mapping` | access control | `mapping_id` | tenant-level role to AD group mapping | new table |
| `table_entity_pending` | pending | `pending_id` | pending dataset version | new table |
| `attribute_entity_pending` | pending | `pending_id` | pending attribute version | new table |
| `table_entity_history` | history | `history_id` | historical dataset version | new table |
| `attribute_entity_history` | history | `history_id` | historical attribute version | new table |

## 3. Layered Model View

The target model can be understood in five layers:

1. Master data layer
   - `domain_entity`
   - `tenant_entity`
2. Current published layer
   - `table_entity`
   - `attribute_entity`
3. Approval request layer
   - `approval_request`
4. Pending approval layer
   - `table_entity_pending`
   - `attribute_entity_pending`
5. History layer
   - `table_entity_history`
   - `attribute_entity_history`

Access control is handled separately by:

- `tenant_role_mapping`

## 4. Relationship Legend

| Symbol | Meaning |
| --- | --- |
| `->` | physical foreign key |
| `=>` | logical association |

## 5. Relationship Matrix

| No. | Source | Relation | Target | Type | Description |
| --- | --- | --- | --- | --- | --- |
| 1 | `tenant_entity.domain_id` | `->` | `domain_entity.id` | physical FK | one tenant belongs to one domain |
| 2 | `table_entity.domain_id` | `->` | `domain_entity.id` | physical FK | one dataset belongs to one domain |
| 3 | `table_entity.tenant_unique_id` | `->` | `tenant_entity.id` | physical FK | one dataset belongs to one tenant |
| 4 | `attribute_entity.table_id` | `->` | `table_entity.id` | physical FK | one attribute belongs to one dataset |
| 5 | `attribute_entity.domain_id` | `=>` | `domain_entity.id` | logical | derived from metadata and expected to match the parent dataset |
| 6 | `attribute_entity.tenant_unique_id` | `=>` | `tenant_entity.id` | logical | derived from metadata and expected to match the parent dataset |
| 7 | `approval_request.domain_id` | `->` | `domain_entity.id` | physical FK | one request belongs to one domain |
| 8 | `approval_request.tenant_unique_id` | `->` | `tenant_entity.id` | physical FK | one request belongs to one tenant |
| 9 | `tenant_role_mapping.domain_id` | `->` | `domain_entity.id` | physical FK | role mapping belongs to a domain |
| 10 | `tenant_role_mapping.tenant_unique_id` | `->` | `tenant_entity.id` | physical FK | role mapping belongs to a tenant |
| 11 | `table_entity.latest_request_id` | `->` | `approval_request.request_id` | physical FK | latest request that produced the current dataset state |
| 12 | `attribute_entity.latest_request_id` | `->` | `approval_request.request_id` | physical FK | latest request that produced the current attribute state |
| 13 | `table_entity_pending.request_id` | `->` | `approval_request.request_id` | physical FK | pending dataset row belongs to one request |
| 14 | `table_entity_pending.target_table_id` | `->` | `table_entity.id` | physical FK | for Update/Delete it points to the current dataset; for Add it can be null |
| 15 | `attribute_entity_pending.request_id` | `->` | `approval_request.request_id` | physical FK | pending attribute row belongs to one request |
| 16 | `attribute_entity_pending.target_attribute_id` | `->` | `attribute_entity.id` | physical FK | for Update/Delete it points to the current attribute; for Add it can be null |
| 17 | `attribute_entity_pending.table_id` | `=>` | `table_entity.id` | logical | points to the parent dataset; in Add scenarios it may need request-internal mapping first |
| 18 | `table_entity_history.table_id` | `->` | `table_entity.id` | physical FK | each historical dataset version belongs to one current logical dataset |
| 19 | `table_entity_history.source_request_id` | `->` | `approval_request.request_id` | physical FK | the request that produced the historical version |
| 20 | `attribute_entity_history.attribute_id` | `->` | `attribute_entity.id` | physical FK | each historical attribute version belongs to one current logical attribute |
| 21 | `attribute_entity_history.source_request_id` | `->` | `approval_request.request_id` | physical FK | the request that produced the historical version |
| 22 | `attribute_entity_history.table_id` | `=>` | `table_entity.id` | logical | used for querying attribute history by dataset |

## 6. Relationship Interpretation

### 6.1 Domain and Tenant

- one `domain_entity` can have many `tenant_entity` records
- `tenant_entity` is the tenant master source
- tenant-level Maker and Checker access control ultimately lands on `tenant_unique_id`

### 6.2 Dataset and Attribute

- one `table_entity` can have many `attribute_entity` records
- `attribute_entity.table_id` is the core parent-child key
- `attribute_entity.domain_id` and `attribute_entity.tenant_unique_id` are redundant derived fields mainly used for filtering and search

### 6.3 Approval Request and Pending Items

- one `approval_request` can contain multiple pending dataset rows
- one `approval_request` can also contain multiple pending attribute rows
- therefore the relationship is `1 : N`
- both bulk upload and UI submit share the same request header model

### 6.4 Current and History

- one current dataset can produce many historical dataset versions
- one current attribute can produce many historical attribute versions
- therefore:
  - `table_entity : table_entity_history = 1 : N`
  - `attribute_entity : attribute_entity_history = 1 : N`
- current tables hold only the latest published state
- history tables hold closed previous versions

### 6.5 Current and Pending

- for one current record, only one `approval_status = 'P'` pending version should exist at a time
- this is enforced by:
  - `table_entity_pending_target_pending_uq`
  - `attribute_entity_pending_target_pending_uq`
- the purpose is to prevent duplicate in-flight submissions for the same target record

### 6.6 Tenant and Role Mapping

- one tenant can have multiple role types
- the current design includes:
  - `REQUESTER`
  - `APPROVER`
  - `VIEWER`
- uniqueness on `(tenant_unique_id, role_type)` ensures only one active mapping per tenant-role pair

## 7. Lifecycle Mapping

### 7.1 Browse Current Published Data

Read source:

- `table_entity`
- `attribute_entity`

Notes:

- the default UI shows current published data
- pending tables are not the default read source

### 7.2 Maker Submits a Change

Write path:

1. create `approval_request`
2. insert rows into `table_entity_pending`
3. insert rows into `attribute_entity_pending`

Notes:

- current tables are not directly updated at submit time
- all changes enter the pending layer first

### 7.3 Checker Approves a Change

Processing path:

1. read the relevant pending rows
2. if the action is Update, archive the old current snapshot into history first
3. insert or update the current record
4. mark the pending rows as approved
5. update the request-level summary status

### 7.4 Checker Rejects a Change

Processing path:

1. keep the pending rows
2. mark the pending rows as rejected
3. update `approval_request` to `REJECTED` or `PARTIALLY_APPROVED`
4. leave the current tables unchanged

## 8. Version Flow

The version chain is:

- current tables store the active published version
- history tables store closed prior versions
- pending tables store the candidate version under review

For Update:

1. current `table_entity.version_seq = N`
2. after submit, `table_entity_pending.target_version_seq = N + 1`
3. after approval:
   - the old current version is archived to history with `version_seq = N`
   - the new current version becomes `version_seq = N + 1`

For Add:

1. the pending target version is `1`
2. after approval, the first current version is `1.0`

For Delete:

- the current phase interprets Delete as disabling the current record
- it does not create a new explicit delete version by default
- if the business later requires delete-as-a-version, the data model and publish rules must be extended

## 9. ASCII ER View

```text
domain_entity
    |
    +--< tenant_entity
            |
            +--< tenant_role_mapping
            |
            +--< approval_request
            |       |
            |       +--< table_entity_pending
            |       |       |
            |       |       +--> table_entity (target on update/delete)
            |       |
            |       +--< attribute_entity_pending
            |               |
            |               +--> attribute_entity (target on update/delete)
            |
            +--< table_entity
                    |
                    +--< attribute_entity
                    |
                    +--< table_entity_history
                    |
                    +-- latest_request_id --> approval_request

attribute_entity
    |
    +--< attribute_entity_history
    |
    +-- latest_request_id --> approval_request
```

## 10. Implementation Notes

- frontend terminology should use `dataset`, not `table`
- backend physical table names can remain unchanged as `table_entity`
- API DTOs should clearly distinguish:
  - `datasetId`
  - `tableEntityId`
  - `requestId`
  - `pendingId`
  - `historyId`
- `attribute_entity_pending.table_id` needs special handling:
  - if the dataset is also new and not yet approved, the flow cannot rely only on current `table_entity.id`
  - bulk upload may need a request-internal mapping between new dataset rows and new attribute rows

## 11. Recommended Review Order

For architecture review and implementation alignment, the recommended order is:

1. this ER page, to align on entity roles and boundaries
2. the target data model document, to align on why the tables are split this way
3. the DDL draft, to confirm the physical schema
4. the Alembic migration checklist, to confirm rollout sequence

## 12. Optional Follow-up Deliverables

If needed, the next useful documents would be:

- a one-page ER summary formatted specifically for Confluence diagrams
- an API field mapping sheet for request and response models
