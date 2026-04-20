# data-dictonary-service

Data Dictionary Service running on Cloud Run with Cloud SQL PostgreSQL.

## Current Project Layout

- `api/`
  - FastAPI routers
- `services/`
  - business logic
- `schemas/`
  - request/response schemas for REST APIs
- `db/`
  - database layer
  - `session.py`: runtime database engine and session management
  - `queries/`: existing raw SQL query modules
  - `models/`: SQLModel table mappings
  - `repositories/`: repository layer for new maker-checker tables
  - `bootstrap.py`: bootstrap helpers
  - `sql/`: bootstrap SQL files
- `alembic/`
  - schema migration scripts
- `docs/`
  - requirements, design notes, data model, migration, and maker-checker documents
- `utils/`
  - shared utilities
- `core/`
  - app configuration and non-database core helpers

## Persistence Strategy

- Existing catalog tables remain on raw SQL under `db/queries/`
- New maker-checker tables use SQLModel under `db/models/`
- New maker-checker write paths are gradually moving to repositories under `db/repositories/`
- Alembic tracks the SQLModel maker-checker tables and hand-maintained live-database migrations

## Current Status

- Service code has been restored.
- Alembic baseline and maker-checker migration chain have been added.
- Submit API and maker-checker foundations are in progress.
