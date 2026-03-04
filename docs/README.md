# DET Coordinator Service

Coordinator service for processing files from SMB, extracting data through FOI, submitting to ITM, notifying iQube on failures, and archiving files.

This service is built with FastAPI and is designed to run on Google Cloud Run.

## What This Service Does

At a high level, one `/api/v1/coordinator/runs` call executes one batch cycle:

1. Scan source files from SMB (temporary file names are filtered out).
2. Group by `remitter + base_name` (timestamp suffix stripped).
3. Process only the latest file in each group.
4. Check file stability on SMB before processing.
5. Claim processing in DB (idempotency guard).
6. Download file and compute MD5.
7. Call FOI extraction.
8. Handle extraction result:
   - `result` -> submit to ITM
   - `failed` -> record extraction failure and notify iQube
   - `not_accepted` -> record only (no ITM / no iQube)
9. Retry latest `ITM_FAILED` records after main batch processing.
10. Schedule archive in background:
   - old versions discovered during scan
   - DB housekeeping candidates (success/ops/not_accepted not archived yet)

## Key Behaviors

- Idempotency is protected by DB claim (`status=processing` unique on `base_name + content_md5`).
- Archive does not block API response for `/coordinator/runs` (background task).
- Archive collision handling is versioned: if target exists, a timestamp+random suffix is appended (no overwrite).
- FOI response content is not logged for success paths.
- Structured JSON logging is used for Cloud Logging and alerting.

## Tech Stack

- Python 3.10
- FastAPI / Uvicorn
- SQLModel + SQLAlchemy (async)
- Alembic
- SMB (`smbprotocol`)
- `httpx` (FOI/ITM/iQube clients)
- Cloud SQL Python Connector (Cloud Run)
- Google Secret Manager

## Project Layout

```text
apis/        FastAPI route handlers
services/    Core business workflows
clients/     External system clients (FOI/ITM/iQube)
db/          Models, DB engine/session, repository (Recorder)
managers/    Token and TLS context managers
deps/        FastAPI dependencies
misc/        Config/constants/utilities
logs/        Structured logging
alembic/     DB migrations
tests/       Unit + integration tests
docs/        Operational docs
```

## APIs

Base prefix: `/api/v1`

- `POST /coordinator/runs`
  - Trigger one coordinator batch run.
- `GET /healthz`
  - Health check.
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`
- `POST /files/{id}/extractions`
  - Retry extraction with password for one record.
- `GET /files/{id}/download`
  - Download source file by record id.
- `GET /files/{id}`
  - Query file detail/history snapshot by id.
- `POST /files/reject`
  - Mark as rejected and archive.

## File Naming / Latest Selection

The service strips timestamp suffixes for grouping latest-vs-old versions.

Supported suffix forms:

- `name_YYYYMMDD_HHMMSS.ext` (for example `filename_20250125_174015.txt`)
- `name_YYYYMMDDHHMMSS.ext`
- `name_YYYYMMDD.ext`

Grouping key = `remitter + stripped_base_name`.

## Configuration

All settings are in `misc/config.py`.

### Minimum local essentials

- `ENV=local`
- `DATABASE_URL`
- `SMB_UNC_PATH`
- `SMB_ARCHIVE_SUBPATH`
- `SMB_USERNAME`
- SMB password via env var name defined by `SMB_SECRET_MANAGER_NAME` (default: `smb-secret`)
- `FOI_API_URL`
- `ITM_API_URL`
- `IQUBE_API_URL`

### Cloud Run essentials

- `ENV` (non-local)
- `PROJECT_ID`
- `INSTANCE_CONNECTION_NAME`
- `DB_IAM_USER`
- `DB_NAME`
- SMB and other secrets in Secret Manager
- Optional UI static path: `UI_DIST_DIR`

### Security/auth related (if used)

- LDAP settings (`LDAP_SERVER_URL`, `LDAP_BIND_DN`, ...)
- JWT settings (`JWT_SECRET_FILE`, ...)
- iQube mTLS settings (`IQUBE_P12`, `IQUBE_P12_PASSWORD`, optional `IQUBE_CA_BUNDLE`)

## Run Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure `.env` (local settings/secrets).

3. Apply DB migrations:

```bash
alembic upgrade head
```

4. Start service:

```bash
uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

## Tests

### Unit tests

```bash
pytest tests -q
```

### Integration tests

See `tests/integration/README.md` and `tests/integration/TEST_CASES.md`.

Typical flow:

1. Start coordinator locally.
2. Configure `.env.it` for real SMB + real Postgres.
3. Run:

```bash
pytest tests/integration -q
```

Notes:
- Pytest fixtures can start fake ITM/iQube/FOI services.
- Some FOI failure tests require `IT_RUN_FOI_FAILURE_TESTS=1`.

## Database Migrations

Alembic is used. Service startup does not run DDL.

- Local:

```bash
alembic upgrade head
```

- New migration:

```bash
alembic revision --autogenerate -m "your message"
```

Cloud Run Job can run the same command with job command override.

See: `docs/db_migrations.md`

## Logging and Alerting

Structured JSON logs are emitted for Cloud Logging.

Recommended docs:

- `docs/logging_alerting.md`

Important fields:

- `event_code`, `client`, `operation`, `status`
- `alertable`, `retryable`, `http_status`, `exception_type`
- `file_basename`, `file_name`, `request_id`, `correlation_id`

## Operational Notes

- The coordinator creates background archive tasks and waits briefly on shutdown.
- For Cloud Run jobs (for example Alembic), set command/args explicitly to avoid using service startup command.
- UI static files can be mounted and served when `UI_DIST_DIR` is configured.

## License / Internal Use

Internal project documentation. Adjust naming/secrets before external sharing.
