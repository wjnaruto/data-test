# SQLModel and Raw SQL Coexistence

## Decision

This project uses a mixed persistence strategy:

- Existing production tables remain on the current raw SQL path.
- New maker-checker tables are defined with SQLModel.
- Alembic tracks only the new SQLModel tables for future autogenerate use.

## Existing Raw SQL Tables

These tables stay outside SQLModel metadata:

- `domain_entity`
- `tenant_entity`
- `table_entity`
- `attribute_entity`
- `glossary`

Reason:

- they already exist in production
- they already have working raw SQL query modules
- they use PostgreSQL-specific `jsonb + generated columns` heavily
- moving them into ORM now would increase migration risk with little short-term value

## SQLModel Tables

These tables are now modeled in:

- [db/models/maker_checker](d:/work/projects/data-dictonary-service/db/models/maker_checker)

Tracked tables:

- `approval_request`
- `tenant_role_mapping`
- `table_entity_pending`
- `attribute_entity_pending`
- `table_entity_history`
- `attribute_entity_history`

## Alembic Behavior

Alembic is configured in:

- [env.py](d:/work/projects/data-dictonary-service/alembic/env.py)

Behavior:

- `target_metadata` points to `SQLModel.metadata`
- only the maker-checker SQLModel tables are included in autogenerate
- existing raw-SQL tables are intentionally filtered out
- minimal legacy table stubs exist in SQLModel metadata only to satisfy foreign-key references from the new tables

This prevents future `alembic revision --autogenerate` from proposing drops or changes for the old raw-SQL tables.

## Recommended Boundary

Use raw SQL for:

- existing catalog read paths
- existing search logic
- existing table / attribute mutation paths until maker-checker publish flow is implemented

Use SQLModel first for:

- maker-checker request tables
- pending/history table reads
- simple request detail and dashboard reads

Keep core publish / approve transactions under explicit SQL control until the new flow is stable.

## Initial Migration Rule

For this project, the first maker-checker migration chain remains hand-maintained:

- [0002_create_request_and_role_tables.py](d:/work/projects/data-dictonary-service/alembic/versions/0002_create_request_and_role_tables.py)
- [0003_add_governance_columns_to_current_tables.py](d:/work/projects/data-dictonary-service/alembic/versions/0003_add_governance_columns_to_current_tables.py)
- [0004_create_pending_and_history_tables.py](d:/work/projects/data-dictonary-service/alembic/versions/0004_create_pending_and_history_tables.py)
- [0005_backfill_current_published_records.py](d:/work/projects/data-dictonary-service/alembic/versions/0005_backfill_current_published_records.py)
- [0006_add_constraints_indexes_and_view.py](d:/work/projects/data-dictonary-service/alembic/versions/0006_add_constraints_indexes_and_view.py)

Revision ids:

- `mc0002_req_role`
- `mc0003_current_cols`
- `mc0004_pending_hist`
- `mc0005_backfill`
- `mc0006_constraints_view`

Reason:

- they define the initial baseline for a live database with existing data
- they include backfill logic
- they include PostgreSQL-specific generated columns, trgm indexes, filtered unique indexes, and view creation

Future revisions can use `--autogenerate` for maker-checker-only schema changes, but this first chain should stay curated.
