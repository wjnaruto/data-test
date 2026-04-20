from traceback import print_tb

from core.config import get_logger
from db.session import db


logger = get_logger(__name__)


def build_conditions(base_query, conditions):
    query = base_query
    values = []
    condition_clauses = []

    for condition, value in conditions:
        if value is not None and value != "":
            condition_clauses.append(condition)
            values.append(value)

    if condition_clauses:
        query += " WHERE " + " AND ".join(condition_clauses)

    return query, values


async def install_extension():
    logger.info("Installing the extension pg_trgm")
    result = await db.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    logger.info("Installed extension pg_trgm")
    return result


async def insert_glossary(metadata):
    query = """
        INSERT INTO glossary (metadata)
        VALUES ($1) RETURNING id \
    """
    record = await db.execute(query, metadata)
    return record
