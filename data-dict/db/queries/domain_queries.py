from core.config import get_logger
from db.session import db


logger = get_logger(__name__)


async def get_domain(name: str):
    query = "SELECT metadata as domain_metadata FROM domain_entity WHERE LOWER(name) = LOWER($1)"
    record = await db.fetch_one(query, name)
    return record


async def insert_domain(id: str, metadata: str):
    query = """
        INSERT INTO domain_entity (fqnhash, metadata)
        VALUES ($1, $2)
            RETURNING id \
    """
    record = await db.execute(query, id, metadata)
    return record


async def update_domain(id: str, metadata: str):
    query = """
        UPDATE domain_entity
           SET metadata = $2
         WHERE id = $1 \
    """
    record = await db.execute(query, id, metadata)
    return record


async def get_all_domain_names():
    query = "SELECT name FROM domain_entity"
    records = await db.fetch_jsonb(query)
    return records


async def delete_domain_metadata_by_domainId(domain_unique_id):
    query = """
        DELETE FROM domain_entity
         WHERE id = $1 \
    """
    return await db.execute(query, domain_unique_id)


async def search_domain_data_dictionary(text):
    domain_query = """
        SELECT metadata FROM domain_entity
         WHERE metadata_text ~* $1 \
    """
    return await db.fetch_jsonb(domain_query, text)
