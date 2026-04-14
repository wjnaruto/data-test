# Alembic Migrations

This project uses Alembic only for schema evolution and data backfill migrations.

Important rules:

- Do not rely on `db/sql/*.sql` bootstrap files for production schema changes after Alembic adoption.
- Use `alembic stamp` once to baseline the existing production schema.
- Run migrations as a separate deployment step, not during Cloud Run container startup.
- Prefer running migrations against a staging clone before production.
- Only the new maker-checker SQLModel tables are tracked by Alembic autogenerate.
- Existing raw-SQL tables remain outside SQLModel metadata on purpose.

Primary environment variable:

- `ALEMBIC_DATABASE_URL`

Example:

```powershell
$env:ALEMBIC_DATABASE_URL="postgresql+psycopg://postgres:password@127.0.0.1:5432/postgres"
alembic -c alembic.ini current
```

Tracked SQLModel tables live in:

- `models/maker_checker/`

Autogenerate example for future maker-checker-only changes:

```powershell
alembic -c alembic.ini revision --autogenerate -m "update maker checker tables"
```
