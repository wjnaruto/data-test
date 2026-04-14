from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from models.maker_checker import ALEMBIC_TRACKED_TABLES
from models import maker_checker  # noqa: F401


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
    return config.get_main_option("sqlalchemy.url")


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


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
