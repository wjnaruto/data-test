import asyncio
from pathlib import Path
from typing import Optional

from core.config import settings
from core.config import get_logger


logger = get_logger(__name__)

_LOCK_KEY = settings.lock_key


async def acquire_advisory_lock(conn, timeout_seconds: int = 120) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while True:
        row = await conn.fetchrow("SELECT pg_try_advisory_lock($1) AS locked;", _LOCK_KEY)
        if row and row["locked"]:
            return True
        if asyncio.get_event_loop().time() > deadline:
            return False
        await asyncio.sleep(0.5)


async def release_advisory_lock(conn):
    await conn.execute("SELECT pg_advisory_unlock($1);", _LOCK_KEY)


async def run_bootstrap(conn, sql_dir: str = "db/sql") -> None:
    sql_dir_path = Path(sql_dir)
    sql_files = sorted(sql_dir_path.glob("*.sql"))
    if not sql_files:
        logger.warning(f"No SQL files found in directory: {sql_dir_path}")
        return

    logger.info(f"Found {len(sql_files)} SQL file(s) in directory: {sql_dir_path}")

    for sql_file in sql_files:
        try:
            sql_text = sql_file.read_text(encoding="utf-8")
            logger.info(f"Executing bootstrap SQL file {sql_file.name}")
            await conn.execute(sql_text)
            logger.info(f"Executed {sql_file.name} successfully")
        except Exception as e:
            logger.error(f"Error executing SQL file {sql_file.name}: {e}", exc_info=True)
            raise
