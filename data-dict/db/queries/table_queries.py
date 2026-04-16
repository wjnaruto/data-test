from core.config import get_logger
from db.session import db
from db.queries.data_access import build_conditions


logger = get_logger(__name__)


async def insert_table(table_metadata: str):
    query = """
        INSERT INTO table_entity (table_metadata)
        VALUES ($1)
            RETURNING id \
    """
    record = await db.execute(query, table_metadata)
    return record


async def update_table(id: str, table_metadata: str):
    query = """
        UPDATE table_entity
        SET table_metadata = $2
        WHERE id = $1 \
    """
    record = await db.execute(query, id, table_metadata)
    return record


async def get_tables(page, size, domain_name, tenant_name, table_name):
    # Query to get the total count of records
    count_query = """
        SELECT COUNT(*)
        FROM table_entity te
            JOIN domain_entity de ON te.domain_id = de.id
            JOIN tenant_entity te2 ON te.tenant_unique_id = te2.id \
    """
    count_query, count_values = build_get_tables_query(count_query, domain_name, tenant_name, table_name)
    total_count = await db.fetch_jsonb(count_query, *count_values)

    # Query to get the paginated data
    data_query = """
        select
            te.table_metadata as table_json,
            de.metadata as domain_json,
            te2.metadata as tenant_json,
            de.id
        from
            table_entity te
                join domain_entity de on te.domain_id = de.id
                join tenant_entity te2 on te.tenant_unique_id = te2.id \
    """
    data_query, data_values = build_get_tables_query(data_query, domain_name, tenant_name, table_name)

    offset = (page - 1) * size
    data_query += f" order by te.table_name LIMIT ${len(data_values) + 1} OFFSET ${len(data_values) + 2}"
    data_values.extend([size, offset])

    records = await db.fetch_jsonb(data_query, *data_values)
    return total_count, records


async def delete_tables_metadata(domain_unique_id, tenant_unique_id):
    # Delete the table_entity records
    query = """
        DELETE FROM table_entity
        WHERE domain_id = $1 AND tenant_unique_id = $2 \
    """
    return await db.execute(query, domain_unique_id, tenant_unique_id)


async def delete_tables_metadata_by_domainId(domain_unique_id):
    query = """
        DELETE FROM table_entity
        WHERE domain_id = $1 \
    """
    return await db.execute(query, domain_unique_id)


def build_get_tables_query(base_query, domain_name, tenant_name, table_name):
    query = base_query
    values = []
    if domain_name:
        query += " WHERE LOWER(de.name) = LOWER($1)"
        values.append(domain_name)
    if tenant_name:
        query += f" {'AND' if domain_name else 'WHERE'} LOWER(te2.name) = LOWER(${len(values) + 1})"
        values.append(tenant_name)
    if table_name:
        query += f" {'AND' if domain_name or tenant_name else 'WHERE'} LOWER(te.table_name) = LOWER(${len(values) + 1})"
        values.append(table_name)
    return query, values


async def get_table_by_table_name_ids(name: str, domain_id: str, tenant_unique_id: str):
    query = """
        select
            te.id, te.table_metadata
        from
            table_entity te
        WHERE te.table_name = $1 AND te.domain_id = $2 AND te.tenant_unique_id = $3 \
    """
    records = await db.fetch_jsonb(query, name, domain_id, tenant_unique_id)
    return records


async def get_table_by_table_name_ids_kba(name: str, product_domain: str, domain_id: str, tenant_unique_id: str):
    query = """
        select
            te.id, te.table_metadata
        from
            table_entity te
        WHERE te.table_name = $1 AND te.domain_id = $2 AND te.tenant_unique_id = $3 AND te.table_metadata ->> 'Product Domain' = $4 \
    """
    records = await db.fetch_jsonb(query, name, domain_id, tenant_unique_id, product_domain)
    return records


async def search_table_data_dictionary(page, size, text, tenant_name, domainId):
    # Define base queries
    base_count_query = "SELECT COUNT(*) FROM table_entity te"
    base_table_query = "SELECT te.table_metadata, de.name FROM table_entity te join domain_entity de on te.domain_id = de.id"

    # Build dynamic conditions
    conditions = []
    if domainId:
        conditions.append(("te.domain_id = $%d" % (len(conditions) + 1), domainId))
    if tenant_name:
        conditions.append(("LOWER(te.tenant_name) = LOWER($%d)" % (len(conditions) + 1), tenant_name))
    if text:
        conditions.append(("te.name_description ~* $%d" % (len(conditions) + 1), text))

    # Build count query
    count_query, count_values = build_conditions(base_count_query, conditions)
    total_count = await db.fetch_jsonb(count_query, *count_values)

    # Build paginated query
    offset = (page - 1) * size
    table_query, table_values = build_conditions(base_table_query, conditions)
    table_query += f" LIMIT ${len(table_values) + 1} OFFSET ${len(table_values) + 2}"
    table_values.extend([size, offset])

    records = await db.fetch_jsonb(table_query, *table_values)
    return total_count, records


async def delete_tables_metadata_by_tenant(tenant_id):
    query = """
        DELETE FROM table_entity
        WHERE tenant_unique_id = $1 \
    """
    return await db.execute(query, tenant_id)
