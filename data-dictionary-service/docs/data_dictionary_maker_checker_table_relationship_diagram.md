# Data Dictionary Maker-Checker Table Relationship Diagram

## 1. Scope

This diagram reflects the current target schema after the maker-checker migration design:

- existing current-state tables
- new request / pending / history tables
- tenant-level role mapping

Note:

- `table_entity` is the current service table that represents `dataset`
- `attribute_entity` represents dataset attributes / fields

## 2. High-Level ER Diagram

```mermaid
erDiagram
    domain_entity ||--o{ tenant_entity : has
    domain_entity ||--o{ table_entity : owns
    tenant_entity ||--o{ table_entity : owns
    table_entity ||--o{ attribute_entity : has

    domain_entity ||--o{ approval_request : scopes
    tenant_entity ||--o{ approval_request : scopes
    domain_entity ||--o{ tenant_role_mapping : scopes
    tenant_entity ||--o{ tenant_role_mapping : scopes

    approval_request ||--o{ table_entity_pending : contains
    approval_request ||--o{ attribute_entity_pending : contains

    table_entity ||--o{ table_entity_pending : target
    attribute_entity ||--o{ attribute_entity_pending : target

    approval_request ||--o{ table_entity_history : source
    approval_request ||--o{ attribute_entity_history : source

    table_entity ||--o{ table_entity_history : versions
    attribute_entity ||--o{ attribute_entity_history : versions

    approval_request {
        varchar request_id PK
        varchar source_type
        varchar domain_id FK
        varchar tenant_unique_id FK
        varchar submitted_by
        varchar request_status
    }

    tenant_role_mapping {
        bigint mapping_id PK
        varchar domain_id FK
        varchar tenant_unique_id FK
        varchar role_type
        varchar ad_group_name
        bool is_active
    }

    domain_entity {
        varchar id PK
        jsonb metadata
        varchar name
    }

    tenant_entity {
        varchar id PK
        varchar domain_id FK
        jsonb metadata
        varchar name
    }

    table_entity {
        varchar id PK
        varchar domain_id FK
        varchar tenant_unique_id FK
        jsonb table_metadata
        int version_seq
        char approval_status
        char record_status
        timestamptz effective_from
        timestamptz effective_to
        varchar latest_request_id FK
    }

    attribute_entity {
        varchar id PK
        varchar table_id FK
        jsonb metadata
        int version_seq
        char approval_status
        char record_status
        timestamptz effective_from
        timestamptz effective_to
        varchar latest_request_id FK
    }

    table_entity_pending {
        varchar pending_id PK
        varchar request_id FK
        varchar target_table_id FK
        jsonb table_metadata
        char dictionary_action
        char approval_status
        int current_version_seq
        int target_version_seq
    }

    attribute_entity_pending {
        varchar pending_id PK
        varchar request_id FK
        varchar target_attribute_id FK
        jsonb metadata
        char dictionary_action
        char approval_status
        int current_version_seq
        int target_version_seq
    }

    table_entity_history {
        varchar history_id PK
        varchar table_id FK
        jsonb table_metadata
        int version_seq
        char dictionary_action
        char approval_status
        char record_status
        timestamptz effective_from
        timestamptz effective_to
        varchar source_request_id FK
    }

    attribute_entity_history {
        varchar history_id PK
        varchar attribute_id FK
        jsonb metadata
        int version_seq
        char dictionary_action
        char approval_status
        char record_status
        timestamptz effective_from
        timestamptz effective_to
        varchar source_request_id FK
    }
```

## 3. Simplified Review View

```text
domain_entity
  └── tenant_entity
        ├── table_entity (current approved dataset)
        │     ├── attribute_entity (current approved attributes)
        │     ├── table_entity_pending (submitted dataset changes)
        │     └── table_entity_history (approved old versions)
        │
        └── approval_request
              ├── table_entity_pending
              └── attribute_entity_pending

attribute_entity
  ├── attribute_entity_pending (submitted attribute changes)
  └── attribute_entity_history (approved old versions)

tenant_role_mapping
  └── defines REQUESTER / APPROVER / VIEWER groups per tenant
```

## 4. Lifecycle Mapping

### Current published records

- `table_entity`
- `attribute_entity`

These are the records shown to normal users after approval.

### Submitted but not yet approved

- `approval_request`
- `table_entity_pending`
- `attribute_entity_pending`

These hold maker submissions waiting for checker action.

### Approved historical versions

- `table_entity_history`
- `attribute_entity_history`

These hold closed versions after a new version is approved and released.

### Access control

- `tenant_role_mapping`

This maps each tenant to AD groups for requester / approver / viewer access.

## 5. Review Notes

When reviewing this with the team, the main things to confirm are:

- `table_entity` continues to represent `dataset`
- `attribute_entity` remains the child table of `table_entity`
- new changes do not go directly into current tables first; they go into `*_pending`
- history tables store approved previous versions only
- `approval_request` is the parent request record for both dataset-level and attribute-level submissions
- `tenant_role_mapping` is tenant-scoped, not global
