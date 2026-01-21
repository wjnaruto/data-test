from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path
from typing import Optional, Tuple

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel

from google.cloud.sql.connector import Connector, IPTypes


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from misc.config import settings  # noqa: E402
from db import models  # noqa: F401,E402  # ensure SQLModel metadata is populated


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def _local_db_url() -> str:
    if settings.DATABASE_URL:
        url = make_url(settings.DATABASE_URL)
        if url.drivername in ("postgres", "postgresql"):
            url = url.set(drivername="postgresql+asyncpg")
        elif url.drivername.startswith("postgres+") and not url.drivername.endswith("+asyncpg"):
            url = url.set(drivername="postgresql+asyncpg")
        return str(url)

    return f"postgresql+asyncpg://{settings.DB_IAM_USER}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Note: for Cloud Run (connector-based) we typically run online migrations only.
    """
    url = _local_db_url() if settings.ENV == "local" else "postgresql://"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def _build_engine_and_connector() -> Tuple[AsyncEngine, Optional[Connector]]:
    if settings.ENV == "local":
        engine = create_async_engine(_local_db_url(), poolclass=pool.NullPool)
        return engine, None

    connector = Connector()

    async def _async_getconn():
        return await connector.connect_async(
            settings.INSTANCE_CONNECTION_NAME,
            driver="asyncpg",
            user=settings.DB_IAM_USER,
            db=settings.DB_NAME,
            ip_type=IPTypes.PRIVATE,
            enable_iam_auth=True,
        )

    engine = create_async_engine(
        "postgresql+asyncpg://",
        poolclass=pool.NullPool,
        async_creator=_async_getconn,
    )
    return engine, connector


def _do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine, connector = await _build_engine_and_connector()
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_do_run_migrations)
    finally:
        await engine.dispose()
        if connector is not None:
            await connector.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

