# Data Dictionary Service Alembic Adoption and Migration Runbook

## 1. Goal

This runbook is for adopting Alembic on top of the existing Cloud SQL PostgreSQL schema and safely introducing the maker-checker data model.

Current facts:

- The service is already deployed on Cloud Run.
- The current tables already exist.
- The current tables already contain production data.
- The project still contains bootstrap SQL for initial schema creation.

Correct approach:

1. Treat the current production schema as the baseline.
2. Stamp that baseline into Alembic.
3. Apply only forward incremental revisions after that.
4. Stop using bootstrap SQL for production schema evolution.

## 2. What Has Been Added

Alembic scaffold:

- [alembic.ini](d:/work/projects/data-dictonary-service/alembic.ini)
- [alembic/env.py](d:/work/projects/data-dictonary-service/alembic/env.py)
- [alembic/README.md](d:/work/projects/data-dictonary-service/alembic/README.md)

Revision skeletons:

- [0001_baseline_existing_schema.py](d:/work/projects/data-dictonary-service/alembic/versions/0001_baseline_existing_schema.py)
- [0002_create_request_and_role_tables.py](d:/work/projects/data-dictonary-service/alembic/versions/0002_create_request_and_role_tables.py)
- [0003_add_governance_columns_to_current_tables.py](d:/work/projects/data-dictonary-service/alembic/versions/0003_add_governance_columns_to_current_tables.py)
- [0004_create_pending_and_history_tables.py](d:/work/projects/data-dictonary-service/alembic/versions/0004_create_pending_and_history_tables.py)
- [0005_backfill_current_published_records.py](d:/work/projects/data-dictonary-service/alembic/versions/0005_backfill_current_published_records.py)
- [0006_add_constraints_indexes_and_view.py](d:/work/projects/data-dictonary-service/alembic/versions/0006_add_constraints_indexes_and_view.py)

Reference input:

- [data_dictionary_maker_checker_target_data_model_ddl_draft.sql](d:/work/projects/data-dictonary-service/docs/data_dictionary_maker_checker_target_data_model_ddl_draft.sql)

## 3. Connection Strategy

Do not run production migrations from Cloud Run application startup.

Use one of these:

- CI/CD runner that can reach Cloud SQL
- Cloud Run Job dedicated to migrations
- Local operator machine with Cloud SQL Auth Proxy

For Alembic, use a normal SQLAlchemy URL through:

- `ALEMBIC_DATABASE_URL`

Example:

```powershell
$env:ALEMBIC_DATABASE_URL="postgresql+psycopg://postgres:password@127.0.0.1:5432/postgres"
alembic -c alembic.ini current
```

## 4. One-Time Baseline Procedure

This must be done once per existing environment.

Baseline revision:

- [0001_baseline_existing_schema.py](d:/work/projects/data-dictonary-service/alembic/versions/0001_baseline_existing_schema.py)

On an existing database:

```powershell
alembic -c alembic.ini stamp 0001_baseline_existing_schema
```

This tells Alembic:

- the current schema already exists
- it must not recreate those tables
- migration management starts from the next revision

## 5. Revision Order

Use this order:

1. `0001_baseline_existing_schema`
2. `mc0002_req_role`
3. `mc0003_current_cols`
4. `mc0004_pending_hist`
5. `mc0005_backfill`
6. `mc0006_constraints_view`

Full upgrade:

```powershell
alembic -c alembic.ini upgrade head
```

Step-by-step upgrade:

```powershell
alembic -c alembic.ini upgrade mc0002_req_role
alembic -c alembic.ini upgrade mc0003_current_cols
alembic -c alembic.ini upgrade mc0004_pending_hist
alembic -c alembic.ini upgrade mc0005_backfill
alembic -c alembic.ini upgrade mc0006_constraints_view
```

## 6. Recommended Rollout

### Stage 1

Clone production into staging/UAT.

### Stage 2

Run:

```powershell
alembic -c alembic.ini stamp 0001_baseline_existing_schema
alembic -c alembic.ini upgrade head
```

### Stage 3

Validate:

- migration runtime
- lock behavior
- row counts
- backfill correctness
- index creation time

### Stage 4

After staging sign-off, run the same process in production during a controlled change window.

## 7. Backfill Semantics

The backfill revision initializes existing records as already-approved current records.

For both `table_entity` and `attribute_entity`:

- `version_seq = 1`
- `approval_status = 'A'`
- `dictionary_action = 'A'`, unless `deleted = true`, then `'D'`
- `record_status = 'A'`, unless `deleted = true`, then `'D'`
- `effective_from` is derived from `createdat`
- `effective_to = NULL`

## 8. Validation SQL

Run after staging and production migration:

```sql
SELECT COUNT(*) AS table_missing_version
FROM public.table_entity
WHERE version_seq IS NULL;

SELECT COUNT(*) AS attribute_missing_version
FROM public.attribute_entity
WHERE version_seq IS NULL;

SELECT COUNT(*) AS table_missing_effective_from
FROM public.table_entity
WHERE effective_from IS NULL;

SELECT COUNT(*) AS attribute_missing_effective_from
FROM public.attribute_entity
WHERE effective_from IS NULL;

SELECT COUNT(*) AS invalid_table_window
FROM public.table_entity
WHERE effective_to IS NOT NULL
  AND effective_to < effective_from;

SELECT COUNT(*) AS invalid_attribute_window
FROM public.attribute_entity
WHERE effective_to IS NOT NULL
  AND effective_to < effective_from;
```

Expected result:

- all counts are `0`

## 9. Production Rules

After Alembic adoption:

- production schema changes must go through Alembic
- [bootstrap.py](d:/work/projects/data-dictonary-service/db/bootstrap.py) should no longer be your production migration mechanism
- set `RUN_BOOTSTRAP_ON_STARTUP=false` in production

Keep bootstrap only for local or disposable environments.

## 10. What You Should Do Next

1. Install Alembic migration dependencies in the runner environment.
2. Review these revision files against the actual live schema.
3. Clone production to staging.
4. Stamp staging with baseline.
5. Run revisions one by one.
6. Measure index creation and decide whether any large index must be changed to `CONCURRENTLY`.
7. After staging sign-off, repeat in production.
