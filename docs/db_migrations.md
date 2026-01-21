# DB migrations (Alembic)

This service uses SQLModel + SQLAlchemy (async) and runs on Cloud Run.

## Goal

- Service startup should not run DDL.
- Schema creation/upgrades should be done explicitly (recommended: Cloud Run Job) via Alembic.

## Local (DATABASE_URL)

From repo root:

- Upgrade to latest:
  - `alembic upgrade head`

- Create a new migration (auto-generate from SQLModel metadata):
  - `alembic revision --autogenerate -m "your message"`

## Cloud Run (Cloud SQL connector)

Run as a Cloud Run Job using the same image as the service:

- Command:
  - `alembic upgrade head`

- Required env vars (same as the service):
  - `ENV` (not `local`)
  - `INSTANCE_CONNECTION_NAME`
  - `DB_IAM_USER`
  - `DB_NAME`

Notes:
- `alembic/env.py` uses `cloud-sql-python-connector` in non-local env.
- Make sure the Job service account has Cloud SQL IAM auth permissions.

