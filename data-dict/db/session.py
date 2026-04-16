import asyncio
import os
from typing import Any, Iterable, Optional

import asyncpg
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings


class _TransactionAdapter:

    def __init__(self, connection: "_ConnectionAdapter"):
        self._connection = connection
        self._transaction = None

    async def __aenter__(self):
        self._transaction = await self._connection._connection.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._transaction is None:
            return
        if exc_type:
            await self._transaction.rollback()
        else:
            await self._transaction.commit()


class _ConnectionAdapter:

    def __init__(self, connection: AsyncConnection):
        self._connection = connection

    async def fetch(self, query: str, *args):
        result = await self._connection.exec_driver_sql(query, args)
        return result.mappings().all()

    async def fetchrow(self, query: str, *args):
        result = await self._connection.exec_driver_sql(query, args)
        return result.mappings().first()

    async def execute(self, query: str, *args):
        result = await self._connection.exec_driver_sql(query, args)
        return result

    def transaction(self):
        return _TransactionAdapter(self)


class _AcquireContext:

    def __init__(self, engine: AsyncEngine):
        self._engine = engine
        self._connection: Optional[AsyncConnection] = None

    async def __aenter__(self):
        self._connection = await self._engine.connect()
        return _ConnectionAdapter(self._connection)

    async def __aexit__(self, exc_type, exc, tb):
        if self._connection is not None:
            await self._connection.close()


class _PoolAdapter:

    def __init__(self, engine: AsyncEngine):
        self._engine = engine

    def acquire(self):
        return _AcquireContext(self._engine)


class Database:

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.pool: Optional[_PoolAdapter] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self.connector: Optional[Connector] = None

    async def connect(self, connect_type):
        if self.engine is not None:
            return

        self.connector = Connector()

        if os.getenv("ENV") == "local":
            self.engine = create_async_engine(
                self._build_local_url(),
                pool_pre_ping=True,
            )
        else:
            async_creator = self._build_cloud_async_creator(connect_type)
            self.engine = create_async_engine(
                "postgresql+asyncpg://",
                async_creator=async_creator,
                pool_pre_ping=True,
            )

        self.pool = _PoolAdapter(self.engine)
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def disconnect(self):
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None

        self.pool = None
        self.session_factory = None

        if self.connector is not None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.connector.close)
            self.connector = None

    async def switch_user(self, connect_type):
        await self.disconnect()
        await self.connect(connect_type)

    async def fetch_jsonb(self, query: str, *args):
        if not self.pool:
            raise Exception("Database connection pool is not initialized.")
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetch_one(self, query: str, *args):
        if not self.pool:
            raise Exception("Database connection pool is not initialized.")
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def execute(self, query: str, *args):
        if not self.pool:
            raise Exception("Database connection pool is not initialized.")
        async with self.pool.acquire() as connection:
            result = await connection.execute(query, *args)
            return str(result)

    async def execute_many(self, query_list: Iterable[str], *args):
        if not self.pool:
            raise Exception("Database connection pool is not initialized.")
        async with self.pool.acquire() as connection:
            result = []
            for query in query_list:
                result_one = await connection.execute(query, *args)
                result.append(str(result_one))
            return str(result)

    def session(self) -> AsyncSession:
        if self.session_factory is None:
            raise Exception("Database session factory is not initialized.")
        return self.session_factory()

    def adapt_connection(self, connection: AsyncConnection) -> _ConnectionAdapter:
        return _ConnectionAdapter(connection)

    def _build_local_url(self) -> str:
        user = settings.iam_user or "45173366"
        database_name = settings.db or "postgres"
        return f"postgresql+asyncpg://{user}@localhost:5432/{database_name}"

    def _build_cloud_async_creator(self, connect_type):
        connector = self.connector
        if connector is None:
            raise RuntimeError("Cloud SQL connector is not initialized.")

        if connect_type == "postgres":

            async def getconn():
                return await connector.connect_async(
                    settings.instance_connection_name,
                    driver="asyncpg",
                    user="postgres",
                    password=settings.postgres_key,
                    db=settings.db,
                    ip_type=IPTypes.PRIVATE,
                )

            return getconn

        async def getconn():
            return await connector.connect_async(
                settings.instance_connection_name,
                driver="asyncpg",
                user=settings.iam_user,
                password=None,
                db=settings.db,
                ip_type=IPTypes.PRIVATE,
                enable_iam_auth=True,
            )

        return getconn


db = Database()
