from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import async_engine_from_config
try:
    import asyncpg
    from google.cloud.sql.connector import Connector, IPTypes
    from sqlmodel import SQLModel
    from core.config import settings
    from db.models.maker_checker import ALEMBIC_TRACKED_TABLES
    from db.models import maker_checker  # noqa: F401
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "Alembic migration dependencies are missing. "
        "Install requirements-migration.txt in the environment used to run Alembic."
    ) from exc


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = SQLModel.metadata


def _resolve_table_name(obj: object, type_: str, name: str | None, compare_to: object | None) -> str | None:
    if type_ == "table":
        return name

    table = getattr(obj, "table", None)
    if table is not None:
        return getattr(table, "name", None)

    parent = getattr(obj, "parent", None)
    if parent is not None:
        return getattr(parent, "name", None)

    if compare_to is not None:
        compare_table = getattr(compare_to, "table", None)
        if compare_table is not None:
            return getattr(compare_table, "name", None)

    return None


def include_object(obj: object, name: str | None, type_: str, reflected: bool, compare_to: object | None) -> bool:
    if name == "alembic_version":
        return False

    table_name = _resolve_table_name(obj, type_, name, compare_to)
    if table_name is None:
        return True

    return table_name in ALEMBIC_TRACKED_TABLES


def get_url() -> str:
    url = os.getenv("ALEMBIC_DATABASE_URL")
    if url:
        return url

    if os.getenv("ENV") == "local":
        return "postgresql+asyncpg://45173366@localhost:5432/postgres"

    user = "postgres" if settings.connect_type == "postgres" else (settings.iam_user or "postgres")
    database_name = settings.db or "postgres"
    return f"postgresql+asyncpg://{user}@localhost/{database_name}"


def use_explicit_database_url() -> bool:
    return bool(os.getenv("ALEMBIC_DATABASE_URL"))


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def get_project_async_creator():
    if os.getenv("ENV") == "local":
        async def local_creator():
            return await asyncpg.connect(
                user="45173366",
                password=None,
                database="postgres",
                host="localhost",
                port=5432,
            )

        return None, local_creator

    connector = Connector()

    if settings.connect_type == "postgres":
        async def cloud_creator():
            return await connector.connect_async(
                settings.instance_connection_name,
                driver="asyncpg",
                user="postgres",
                password=settings.postgres_key,
                db=settings.db,
                ip_type=IPTypes.PRIVATE,
            )
    else:
        async def cloud_creator():
            return await connector.connect_async(
                settings.instance_connection_name,
                driver="asyncpg",
                user=settings.iam_user,
                password=None,
                db=settings.db,
                ip_type=IPTypes.PRIVATE,
                enable_iam_auth=True,
            )

    return connector, cloud_creator


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online_sync() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


async def run_migrations_online_async() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connector = None
    async_creator = None
    if not use_explicit_database_url():
        connector, async_creator = await get_project_async_creator()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
        async_creator=async_creator,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()
        if connector is not None:
            await asyncio.get_running_loop().run_in_executor(None, connector.close)


if context.is_offline_mode():
    run_migrations_offline()
else:
    url = get_url()
    if use_explicit_database_url() and "+asyncpg" not in url:
        run_migrations_online_sync()
    else:
        asyncio.run(run_migrations_online_async())
