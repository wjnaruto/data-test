# Alembic Setup Checklist

## Packages

Install in the environment that will run migrations:

- `alembic`
- `sqlalchemy`
- `psycopg[binary]`

Example:

```powershell
pip install alembic sqlalchemy "psycopg[binary]"
```

## Environment Variable

Set:

- `ALEMBIC_DATABASE_URL`

Example:

```powershell
$env:ALEMBIC_DATABASE_URL="postgresql+psycopg://postgres:password@127.0.0.1:5432/postgres"
```

## Commands

Current revision:

```powershell
alembic -c alembic.ini current
```

Stamp existing DB:

```powershell
alembic -c alembic.ini stamp 0001_baseline_existing_schema
```

Upgrade all:

```powershell
alembic -c alembic.ini upgrade head
```

Upgrade step by step:

```powershell
python -m alembic -c alembic.ini upgrade mc0002_req_role
python -m alembic -c alembic.ini upgrade mc0003_current_cols
python -m alembic -c alembic.ini upgrade mc0004_pending_hist
python -m alembic -c alembic.ini upgrade mc0005_backfill
python -m alembic -c alembic.ini upgrade mc0006_constraints_view
```
