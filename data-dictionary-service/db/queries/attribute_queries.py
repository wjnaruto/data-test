from core.config import get_logger
from db.session import db
from db.queries.data_access import build_conditions


logger = get_logger(__name__)


async def insert_attribute(metadata):
    query = """
        INSERT INTO attribute_entity (metadata)
        VALUES ($1) RETURNING id \
    """
    record = await db.execute(query, metadata)
    return None


async def update_attribute(attribute_unique_id, metadata):
    query = """
        UPDATE attribute_entity
        SET metadata = $2
        WHERE id = $1 \
    """
    record = await db.execute(query, attribute_unique_id, metadata)
    return record


async def get_attribute_by_name_table_id(attribute_name, table_unique_id, tenant_unique_id):
    query = """
        select te.id,
               te.metadata
        from attribute_entity te
        WHERE te.field_name = $1
          AND te.table_id = $2
          AND te.tenant_unique_id = $3 \
    """
    records = await db.fetch_jsonb(query, attribute_name, table_unique_id, tenant_unique_id)
    return records


async def get_attribute_by_name_table_id_kba(attribute_name, product_domain, table_unique_id, tenant_unique_id):
    query = """
        select te.id,
               te.metadata
        from attribute_entity te
        WHERE te.field_name = $1
          AND te.table_id = $2
          AND te.tenant_unique_id = $3
          AND te.metadata ->> 'Product Domain' = $4 \
    """
    records = await db.fetch_jsonb(query, attribute_name, table_unique_id, tenant_unique_id, product_domain)
    return records


async def delete_attributes_metadata(domain_unique_id, tenant_unique_id):
    # Delete the attribute_entity records
    query = """
        DELETE
        FROM attribute_entity
        WHERE domain_id = $1
          AND tenant_unique_id = $2 \
    """
    return await db.execute(query, domain_unique_id, tenant_unique_id)


async def delete_attributes_metadata_by_domainId(domain_id):
    query = """
        DELETE
        FROM attribute_entity
        WHERE domain_id = $1 \
    """
    return await db.execute(query, domain_id)


async def delete_attributes_metadata_by_tenant(tenant_id):
    query = """
        DELETE
        FROM attribute_entity
        WHERE tenant_unique_id = $1 \
    """
    return await db.execute(query, tenant_id)


async def search_attribute_data_dictionary(page, size, text, tenant_name, domainId):
    # Define base queries
    base_count_query = "SELECT COUNT(*) FROM attribute_entity ae"
    base_attribute_query = "SELECT ae.metadata, de.name FROM attribute_entity ae JOIN domain_entity de ON ae.domain_id = de.id"

    # Define query conditions
    conditions = []
    if domainId:
        conditions.append(("ae.domain_id = $%d" % (len(conditions) + 1), domainId))
    if tenant_name:
        conditions.append(("LOWER(ae.tenant_name) = LOWER($%d)" % (len(conditions) + 1), tenant_name))
    if text:
        conditions.append(("ae.name_description ~* $%d" % (len(conditions) + 1), text))

    # Build count query
    count_query, count_values = build_conditions(base_count_query, conditions)
    total_count = await db.fetch_jsonb(count_query, *count_values)

    # Build paginated query
    offset = (page - 1) * size
    attribute_query, attribute_values = build_conditions(base_attribute_query, conditions)
    attribute_query += f" LIMIT ${len(attribute_values) + 1} OFFSET ${len(attribute_values) + 2}"
    attribute_values.extend([size, offset])

    records = await db.fetch_jsonb(attribute_query, *attribute_values)
    return total_count, records


async def get_attributes_by_table_id(page, size, table_id):
    count_query = """
        SELECT COUNT(*)
        FROM attribute_entity ae
        where ae.table_id = $1 \
    """
    total_count = await db.fetch_jsonb(count_query, table_id)

    data_query = """
        SELECT ae.metadata
        FROM attribute_entity ae
        where ae.table_id = $1 \
    """
    offset = (page - 1) * size
    data_query += f" order by ae.metadata ->>'Is Primary Key' desc, ae.field_name asc LIMIT $2 OFFSET $3"

    records = await db.fetch_jsonb(data_query, table_id, size, offset)
    return total_count, records
