-- Domain
CREATE TABLE IF NOT EXISTS public.domain_entity (
    id varchar(36) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'id'::text))) STORED,
    "name" varchar(256) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'name'::text))) STORED,
    fqnhash varchar(256) NOT NULL,
    metadata jsonb NOT NULL,
    updatedat int8 NOT NULL GENERATED ALWAYS AS ((metadata ->> 'updatedAt'::text)::bigint) STORED,
    updatedby varchar(256) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'updatedBy'::text))) STORED,
    createdat int8 NOT NULL GENERATED ALWAYS AS ((metadata ->> 'createdAt'::text)::bigint) STORED,
    metadata_text text NULL GENERATED ALWAYS AS (metadata::text) STORED,
    CONSTRAINT domain_entity_fqnhash_key UNIQUE (fqnhash),
    CONSTRAINT domain_entity_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS domain_entity_metadata_text_gin_trgm_idx
ON public.domain_entity USING gin (metadata_text gin_trgm_ops);

drop index if exists domain_entity_metadata_text_gist_trgm_idx;

-- Tenant
CREATE TABLE IF NOT EXISTS public.tenant_entity (
    id varchar(36) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'id'::text))) STORED,
    "name" varchar(256) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'tenant_name'::text))) STORED,
    metadata jsonb NOT NULL,
    updatedat int8 NOT NULL GENERATED ALWAYS AS ((metadata ->> 'updatedAt'::text)::bigint) STORED,
    updatedby varchar(256) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'updatedBy'::text))) STORED,
    createdat int8 NOT NULL GENERATED ALWAYS AS ((metadata ->> 'createdAt'::text)::bigint) STORED,
    domain_id varchar(36) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'domainId'::text))) STORED,
    metadata_text text NULL GENERATED ALWAYS AS (metadata::text) STORED,
    name_description text NULL GENERATED ALWAYS AS (
        (
            '{"Tenant ID": "' || COALESCE(metadata ->> 'Tenant ID'::text, '') ||
            '", "Tenant Name": "' || (metadata ->> 'tenant_name'::text) ||
            '", "Tenant Description": "' || COALESCE(metadata ->> 'Tenant Description'::text, '') || '"}'
        )
    ) STORED,
    CONSTRAINT tenant_entity_pkey PRIMARY KEY (id),
    CONSTRAINT tenant_entity_domain_id_fkey FOREIGN KEY (domain_id) REFERENCES public.domain_entity(id)
);

CREATE INDEX IF NOT EXISTS tenant_entity_metadata_text_gin_trgm_idx
ON public.tenant_entity USING gin (metadata_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS tenant_entity_name_description_gin_trgm_idx
ON public.tenant_entity USING gin (name_description gin_trgm_ops);

drop index if exists tenant_entity_metadata_text_gist_trgm_idx;
drop index if exists tenant_entity_name_description_gist_trgm_idx;

-- Table
CREATE TABLE IF NOT EXISTS public.table_entity (
    id varchar(36) NOT NULL GENERATED ALWAYS AS (((table_metadata ->> 'id'::text))) STORED,
    table_name varchar(256) NOT NULL GENERATED ALWAYS AS (((table_metadata ->> 'tableName'::text))) STORED,
    tenant_name varchar(256) NOT NULL GENERATED ALWAYS AS (((table_metadata ->> 'tenantName'::text))) STORED,
    table_metadata jsonb NOT NULL,
    updatedat int8 NOT NULL GENERATED ALWAYS AS ((table_metadata ->> 'updatedAt'::text)::bigint) STORED,
    updatedby varchar(256) NOT NULL GENERATED ALWAYS AS (((table_metadata ->> 'updatedBy'::text))) STORED,
    deleted bool NULL GENERATED ALWAYS AS ((table_metadata ->> 'deleted'::text)::boolean) STORED,
    createdat int8 NOT NULL GENERATED ALWAYS AS ((table_metadata ->> 'createdAt'::text)::bigint) STORED,
    attributes_metadata jsonb NULL GENERATED ALWAYS AS ((table_metadata ->> 'attributesMetadata'::text)::jsonb) STORED,
    domain_id varchar(36) NOT NULL GENERATED ALWAYS AS (((table_metadata ->> 'domainId'::text))) STORED,
    tenant_unique_id varchar(36) NOT NULL GENERATED ALWAYS AS (((table_metadata ->> 'tenantUniqueId'::text))) STORED,
    table_metadata_text text NULL GENERATED ALWAYS AS (table_metadata ->> 'tableInfoMetadata'::text) STORED,
    name_description text NULL GENERATED ALWAYS AS (
        (
            '{"Table Name": "' || COALESCE(table_metadata ->> 'Table Name'::text, table_metadata ->> 'tableName'::text) ||
            '", "Table Description": "' || COALESCE(table_metadata ->> 'Table Description'::text, table_metadata ->> 'Template Description'::text) || '"}'
        )
    ) STORED,
    CONSTRAINT table_entity_pkey PRIMARY KEY (id),
    CONSTRAINT table_entity_domain_id_fkey FOREIGN KEY (domain_id) REFERENCES public.domain_entity(id),
    CONSTRAINT table_entity_tenant_id_fkey FOREIGN KEY (tenant_unique_id) REFERENCES public.tenant_entity(id)
);

CREATE INDEX IF NOT EXISTS table_entity_table_metadata_text_gin_trgm_idx
ON public.table_entity USING gin (table_metadata_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS table_entity_name_description_gin_trgm_idx
ON public.table_entity USING gin (name_description gin_trgm_ops);

drop index if exists table_entity_table_metadata_text_gist_trgm_idx;
drop index if exists table_entity_name_description_gist_trgm_idx;

-- Attribute
CREATE TABLE IF NOT EXISTS public.attribute_entity (
    id varchar(36) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'id'::text))) STORED,
    field_name varchar(256) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'Field Name'::text))) STORED,
    table_name varchar(256) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'Table Name'::text))) STORED,
    tenant_name varchar(256) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'tenantName'::text))) STORED,
    metadata jsonb NOT NULL,
    updatedat int8 NOT NULL GENERATED ALWAYS AS ((metadata ->> 'updatedAt'::text)::bigint) STORED,
    updatedby varchar(256) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'updatedBy'::text))) STORED,
    deleted bool NULL GENERATED ALWAYS AS ((metadata ->> 'deleted'::text)::boolean) STORED,
    createdat int8 NOT NULL GENERATED ALWAYS AS ((metadata ->> 'createdAt'::text)::bigint) STORED,
    domain_id varchar(36) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'domainId'::text))) STORED,
    tenant_unique_id varchar(36) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'tenantUniqueId'::text))) STORED,
    tenant_id varchar(36) NULL GENERATED ALWAYS AS (((metadata ->> 'tenantId'::text))) STORED,
    table_id varchar(36) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'tableId'::text))) STORED,
    metadata_text text NULL GENERATED ALWAYS AS (metadata::text) STORED,
    name_description text NULL GENERATED ALWAYS AS (
        (
            '{"Field Name": "' || (metadata ->> 'Field Name'::text) ||
            '", "Field Description": "' || COALESCE((metadata ->> 'Field Description (Long)'::text), (metadata ->> 'Field Description'::text)) || '"}'
        )
    ) STORED,
    table_description text NULL GENERATED ALWAYS AS (((metadata ->> 'Table Description'::text))) STORED,
    CONSTRAINT attribute_entity_pkey PRIMARY KEY (id),
    CONSTRAINT attribute_entity_table_id_fkey FOREIGN KEY (table_id) REFERENCES public.table_entity(id)
);

CREATE INDEX IF NOT EXISTS attribute_entity_metadata_text_gin_trgm_idx
ON public.attribute_entity USING gin (metadata_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS attribute_entity_name_description_gin_trgm_idx
ON public.attribute_entity USING gin (name_description gin_trgm_ops);

drop index if exists attribute_entity_metadata_text_gist_trgm_idx;
drop index if exists attribute_entity_name_description_gist_trgm_idx;

-- Glossary
CREATE TABLE IF NOT EXISTS public.glossary (
    id varchar(36) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'id'::text))) STORED,
    glossary_key text NOT NULL GENERATED ALWAYS AS (((metadata ->> 'glossary_key'::text))) STORED,
    field_name varchar(256) NOT NULL GENERATED ALWAYS AS (((metadata ->> 'Field Name'::text))) STORED,
    description text NOT NULL GENERATED ALWAYS AS (((metadata ->> 'Field Description'::text))) STORED,
    metadata jsonb NOT NULL,
    deleted bool NOT NULL DEFAULT false,
    CONSTRAINT glossary_pk PRIMARY KEY (glossary_key)
);
CREATE INDEX IF NOT EXISTS glossary_glossary_key_gin_trgm_idx ON public.glossary USING gin (glossary_key gin_trgm_ops);