from core.config import get_logger
from db.session import db
from db.queries.data_access import build_conditions


logger = get_logger(__name__)


async def get_tenants(tenant_name: str, domain_name: str):
    query = """
        select te.metadata as tenant_metadata,
               te2.metadata as domain_metadata
        from
            tenant_entity te
                join domain_entity te2 on
                    te.domain_id = te2.id
        where \
    """
    values = []
    if tenant_name:
        query += " LOWER(te.name) = LOWER($1)"
        values.append(tenant_name)
    if domain_name:
        query += f" {'AND' if tenant_name else ''} LOWER(te2.name) = LOWER(${len(values) + 1})"
        values.append(domain_name)
    query += " ORDER BY te.name"
    records = await db.fetch_jsonb(query, *values)
    return records


async def insert_tenant(metadata: str):
    query = """
        INSERT INTO tenant_entity (metadata)
        VALUES ($1)
            RETURNING id \
    """
    record = await db.execute(query, metadata)
    return record


async def update_tenant(id: str, metadata: str):
    query = """
        UPDATE tenant_entity
        SET metadata = $2
        WHERE id = $1 \
    """
    record = await db.execute(query, id, metadata)
    return record


async def delete_tenant(id: str):
    query = "DELETE FROM tenant_entity WHERE id = $1"
    record = await db.execute(query, id)
    return record


async def delete_tenants_metadata_by_domainId(domain_unique_id):
    query = """
        DELETE FROM tenant_entity
        WHERE domain_id = $1 \
    """
    return await db.execute(query, domain_unique_id)


async def get_all_tenants_names():
    query = "SELECT name FROM tenant_entity"
    records = await db.fetch_jsonb(query)
    return records


async def search_tenant_data_dictionary(text, tenant_name, domainId):
    # Define base query
    base_tenant_query = "SELECT te.metadata, de.name FROM tenant_entity te join domain_entity de on te.domain_id = de.id"

    # Build dynamic conditions
    conditions = []
    if domainId:
        conditions.append(("te.domain_id = $%d" % (len(conditions) + 1), domainId))
    if tenant_name:
        conditions.append(("LOWER(te.name) = LOWER($%d)" % (len(conditions) + 1), tenant_name))
    if text:
        conditions.append(("te.name_description ~* $%d" % (len(conditions) + 1), text))

    # Build query
    tenant_query, tenant_values = build_conditions(base_tenant_query, conditions)
    records = await db.fetch_jsonb(tenant_query, *tenant_values)
    return records


async def delete_tenants_metadata_by_tenant(tenant_id):
    query = """
        DELETE FROM tenant_entity
        WHERE id = $1 \
    """
    return await db.execute(query, tenant_id)
