from typing import Any, List, Tuple

import psycopg2
from sqlalchemy.engine.url import make_url

def _normalize_db_url(db_url: str) -> dict[str, Any]:
    url = make_url(db_url)

    if url.drivername.startswith("postgres+"):
        url = url.set(drivername="postgresql")

    return {
        "host": url.host or "localhost",
        "port": url.port or 5432,
        "user": url.username or "postgres",
        "password": url.password or "",
        "dbname": url.database or "postgres",
    }

def db_fetch_statuses(db_url: str, file_name_like: str) -> List[Tuple]:
    params = _normalize_db_url(db_url)

    with psycopg2.connect(**params) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT file_name, status, message, attempt_no, created_at
                FROM coordinator_control
                WHERE file_name LIKE %s
                ORDER BY created_at ASC
                """,
                (file_name_like,),
            )
            return cur.fetchall()


def db_delete_statuses(db_url: str, file_names: list[str]) -> int:
    """
    Delete all rows for the given exact file_name values.
    Returns the number of deleted rows.
    """
    names = [x for x in (file_names or []) if x]
    if not names:
        return 0

    params = _normalize_db_url(db_url)

    with psycopg2.connect(**params) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM coordinator_control WHERE file_name = ANY(%s)",
                (names,),
            )
            return int(cur.rowcount or 0)
