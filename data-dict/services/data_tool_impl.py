import json
import os
import re
import uuid
from datetime import datetime
import google.auth
import pandas as pd
from fastapi import HTTPException
from google.cloud import storage
from core.config import get_logger, settings
from db.queries import data_access, domain_queries, tenant_queries, table_queries, attribute_queries, glossary_queries


logger = get_logger(__name__)


class DataToolService:

    async def insert_data(self, key, file_name, template_type):
        try:
            # check key
            project_id = settings.project_id
            data_key = settings.data_key
            if key != data_key:
                return "Key not found"

            download_path = await self.download_file_from_gcp(project_id, file_name)

            # Get the sheet names for the given file
            service_account_name = await self.get_service_account_name()
            if template_type.lower() == 'mesh':
                producer_data = await self.excel_to_data(download_path, target_sheet_name='Producer')
                datasets_data = await self.excel_to_data(download_path, target_sheet_name='Data Sets')
                attributes_data = await self.excel_to_data(download_path, target_sheet_name='Attributes')
                domain_name, domain_unique_id = await self.insert_or_update_domain_metadata(producer_data, service_account_name)
                tenant_name, tenant_unique_id, tenant_id = await self.insert_or_update_tenant_metadata(
                    domain_name, domain_unique_id, producer_data, service_account_name)
                await self.insert_or_update_table_metadata(
                    attributes_data, datasets_data, domain_unique_id, service_account_name, tenant_unique_id, tenant_name, tenant_id)
            elif template_type.lower() == 'kba':
                templates_data = await self.excel_to_data(download_path, target_sheet_name='DataDict')
                fields_data = await self.excel_to_data(download_path, target_sheet_name='DataDict')
                domain_names_ids = await self.insert_or_update_domain_metadata_kba(templates_data, service_account_name)
                tenants_names_ids = await self.insert_or_update_tenant_metadata_kba(domain_names_ids, templates_data, service_account_name)
                await self.insert_or_update_table_metadata_kba(fields_data, templates_data, service_account_name, tenants_names_ids)
            return "Data inserted successfully"
        except Exception as e:
            logger.error(f"Error inserting or updating data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def download_file_from_gcp(self, project_id, file_name):
        logger.info("Start downloading the data file...")

        client = storage.Client(project=project_id)

        bucket_name = f"{project_id}-data-dictionary"
        file_key = f"data/{file_name}"
        download_path = f"/app/{file_name}"

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_key)
        blob.download_to_filename(download_path)

        if not os.path.exists(download_path):
            raise HTTPException(status_code=500, detail="File download failed")
        logger.info("End downloading the data file, path: %s", download_path)
        return download_path

    async def download_glossary_file_from_gcp(self, project_id, file_name):
        logger.info("Start downloading the data file...")

        client = storage.Client(project=project_id)

        bucket_name = f"{project_id}-data-dictionary"
        file_key = f"data/{file_name}"
        download_path = f"/app/{file_name}"
        os.makedirs(os.path.dirname(download_path), exist_ok=True)

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_key)
        blob.download_to_filename(download_path)

        if not os.path.exists(download_path):
            raise HTTPException(status_code=500, detail="File download failed")
        logger.info("End downloading the data file, path: %s", download_path)
        return download_path

    async def insert_or_update_domain_metadata(self, producer_data, service_account_name):
        domain_name = producer_data[0]['Domain']
        domain_unique_id = str(uuid.uuid4())
        domain_metadata = {
            'id': domain_unique_id,
            'name': domain_name,
            'createdAt': int(datetime.now().timestamp()),
            'updatedAt': int(datetime.now().timestamp()),
            'updatedBy': service_account_name,
        }
        domain_exist_data = await domain_queries.get_domain(domain_name)
        if domain_exist_data:
            data_exist = json.loads(domain_exist_data['domain_metadata'])
            domain_unique_id = data_exist.get('id')
            domain_metadata['id'] = domain_unique_id
            domain_metadata['createdAt'] = int(data_exist.get('createdAt'))
            await domain_queries.update_domain(domain_metadata['id'], json.dumps(domain_metadata))
        else:
            await domain_queries.insert_domain(domain_metadata['id'], json.dumps(domain_metadata))
        return domain_name, domain_unique_id

    async def insert_or_update_domain_metadata_kba(self, templates_data, service_account_name):
        domain_names = list(set([item['Product'] for item in templates_data]))
        templates_data_by_domain = {domain: [] for domain in domain_names}
        for item in templates_data:
            templates_data_by_domain[item['Product']].append(item)
        domain_names_ids = []
        for domain_name, templates in templates_data_by_domain.items():
            domain_unique_id = str(uuid.uuid4())
            domain_metadata = {
                'id': domain_unique_id,
                'name': domain_name,
                'createdAt': int(datetime.now().timestamp()),
                'updatedAt': int(datetime.now().timestamp()),
                'updatedBy': service_account_name,
            }
            domain_exist_data = await domain_queries.get_domain(domain_name)
            if domain_exist_data:
                data_exist = json.loads(domain_exist_data['domain_metadata'])
                domain_unique_id = data_exist.get('id')
                domain_metadata['id'] = domain_unique_id
                domain_metadata['createdAt'] = int(data_exist.get('createdAt'))
                await domain_queries.update_domain(domain_metadata['id'], json.dumps(domain_metadata))
            else:
                await domain_queries.insert_domain(domain_metadata['id'], json.dumps(domain_metadata))
            domain_names_ids.append({'domain_unique_id': domain_unique_id, 'domain_name': domain_name})
        return domain_names_ids

    async def insert_or_update_tenant_metadata(self, domain_name, domain_unique_id, producer_data, service_account_name):
        tenant_unique_id = str(uuid.uuid4())
        tenant_name = producer_data[0]['Tenant Name']
        current_timestamp = int(datetime.now().timestamp())
        raw_eim = producer_data[0]['Source System EIM ID(s)']
        if raw_eim is None:
            cleaned_eim = None
        elif isinstance(raw_eim, float) and raw_eim.is_integer():
            cleaned_eim = str(int(raw_eim))
        else:
            cleaned_eim = str(raw_eim)
        producer_data[0]['Source System EIM ID(s)'] = cleaned_eim

        tenant_metadata_dict = {
            'id': tenant_unique_id,
            'tenant_name': tenant_name,
            'updatedAt': current_timestamp,
            'updatedBy': service_account_name,
            'createdAt': current_timestamp,
            'domainId': domain_unique_id,
            **producer_data[0]
        }

        tenant_exist_data = await tenant_queries.get_tenants(tenant_name, domain_name)
        if tenant_exist_data:
            tenant_json = json.loads(tenant_exist_data[0]['tenant_metadata'])
            tenant_unique_id = tenant_json.get('id')
            tenant_metadata_dict['id'] = tenant_unique_id
            tenant_metadata_dict['createdAt'] = int(tenant_json.get('createdAt'))
            await tenant_queries.update_tenant(tenant_metadata_dict['id'], json.dumps(tenant_metadata_dict))
        else:
            await tenant_queries.insert_tenant(json.dumps(tenant_metadata_dict))
        tenant_id = tenant_metadata_dict['Tenant ID']
        return tenant_name, tenant_unique_id, tenant_id

    async def insert_or_update_tenant_metadata_kba(self, domain_names_ids, templates_data, service_account_name):
        tenants_names_ids = []
        for domain in domain_names_ids:
            domain_unique_id = domain.get('domain_unique_id')
            domain_name = domain.get('domain_name')
            current_timestamp = int(datetime.now().timestamp())
            templates_data_by_domain = [item for item in templates_data if item['Product'] == domain_name]

            tenant_unique_id = str(uuid.uuid4())
            tenant_name = templates_data_by_domain[0]['Product']

            tenant_metadata_dict = {
                'id': tenant_unique_id,
                'tenant_name': tenant_name,
                'updatedAt': current_timestamp,
                'updatedBy': service_account_name,
                'createdAt': current_timestamp,
                'domainId': domain_unique_id
            }
            tenant_exist_data = await tenant_queries.get_tenants(tenant_name, domain_name)
            if tenant_exist_data:
                tenant_json = json.loads(tenant_exist_data[0]['tenant_metadata'])
                tenant_unique_id = tenant_json.get('id')
                tenant_metadata_dict['id'] = tenant_unique_id
                tenant_metadata_dict['createdAt'] = int(tenant_json.get('createdAt'))
                await tenant_queries.update_tenant(tenant_metadata_dict['id'], json.dumps(tenant_metadata_dict))
            else:
                await tenant_queries.insert_tenant(json.dumps(tenant_metadata_dict))
            tenants_names_ids.append({'tenant_unique_id': tenant_unique_id, 'tenant_name': tenant_name,
                                      'domain_unique_id': domain_unique_id, 'domain_name': domain_name})
        return tenants_names_ids

    async def insert_or_update_table_metadata(self, attributes_data, datasets_data, domain_unique_id, service_account_name,
                                              tenant_unique_id, tenant_name, tenant_id):
        # delete before insert
        logger.info("Delete tables metadata of domain %s and tenant %s", domain_unique_id, tenant_unique_id)
        delete_table_result = await table_queries.delete_tables_metadata(domain_unique_id, tenant_unique_id)
        logger.info(delete_table_result)

        logger.info("Delete attributes metadata of domain %s and tenant %s", domain_unique_id, tenant_unique_id)
        delete_attributes_result = await attribute_queries.delete_attributes_metadata(domain_unique_id, tenant_unique_id)
        logger.info(delete_attributes_result)

        table_dict = {table['Table Name']: table for table in datasets_data}
        for attribute in attributes_data:
            table_name = attribute['Table Name']
            if table_name in table_dict:
                if 'attributesMetadata' not in table_dict[table_name]:
                    table_dict[table_name]['attributesMetadata'] = []
                table_dict[table_name]['attributesMetadata'].append(attribute)
            else:
                table_dict[table_name] = {'Table Name': table_name, 'attributesMetadata': ['']}
        combined_data = list(table_dict.values())
        combined_data = [item for item in combined_data if item.get('Table Name') and item.get('Tenant Name') and item.get('Table Description')]
        for record in combined_data:
            unique_id = str(uuid.uuid4())
            current_timestamp = int(datetime.now().timestamp())
            record['id'] = unique_id
            record['deleted'] = False
            record['domainId'] = domain_unique_id
            record['tenantUniqueId'] = tenant_unique_id
            record['createdAt'] = current_timestamp
            record['updatedAt'] = current_timestamp
            record['updatedBy'] = service_account_name
            record['tableName'] = record['Table Name']
            record['tenantName'] = tenant_name
            record['tenantId'] = tenant_id
            record['tableInfoMetadata'] = json.dumps({k: v for k, v in record.items() if k != 'attributesMetadata'})

            # Insert new table
            await table_queries.insert_table(json.dumps(record))

            # insert attributes metadata
            if 'attributesMetadata' in record and record['attributesMetadata']:
                table_unique_id = record['id']
                table_description = str(record['Table Description'])
                for attirbute_record in record['attributesMetadata']:
                    if attirbute_record != '':
                        attribute_unique_id = str(uuid.uuid4())
                        current_timestamp = int(datetime.now().timestamp())
                        attirbute_record = {
                            'id': attribute_unique_id,
                            'tableId': table_unique_id,
                            'domainId': domain_unique_id,
                            'tenantUniqueId': tenant_unique_id,
                            'tenantId': tenant_id,
                            'createdAt': current_timestamp,
                            'updatedAt': current_timestamp,
                            'updatedBy': service_account_name,
                            'deleted': False,
                            'tenantName': tenant_name,
                            'Table Description': table_description,
                            **attirbute_record
                        }

                        await attribute_queries.insert_attribute(json.dumps(attirbute_record))

    async def insert_or_update_table_metadata_kba(self, fields_data, templates_data, service_account_name, tenants_names_ids):
        for tenant_name_id in tenants_names_ids:
            tenant_unique_id = tenant_name_id.get('tenant_unique_id')
            tenant_name = tenant_name_id.get('tenant_name')
            domain_unique_id = tenant_name_id.get('domain_unique_id')
            domain_name = tenant_name_id.get('domain_name')
            templates_data_by_tenant = [
                {**item, 'filed_list': [field for field in fields_data
                                        if field['Product Domain'] == item['Product Domain'] and field['Template Name'] == item['Template Name']]}
                for item in templates_data if item['Product'] == tenant_name
            ]

            for record in templates_data_by_tenant:
                unique_id = str(uuid.uuid4())
                current_timestamp = int(datetime.now().timestamp())
                record['id'] = unique_id
                record['deleted'] = False
                record['domainId'] = domain_unique_id
                record['tenantUniqueId'] = tenant_unique_id
                record['createdAt'] = current_timestamp
                record['updatedAt'] = current_timestamp
                record['updatedBy'] = service_account_name
                record['tableName'] = record['Template Name']
                record['tenantName'] = tenant_name

                existing_table = await table_queries.get_table_by_table_name_ids_kba(
                    record['Template Name'], record['Product Domain'], domain_unique_id, tenant_unique_id)
                if existing_table:
                    # Update existing table
                    table_json = json.loads(existing_table[0]['table_metadata'])
                    table_unique_id = table_json.get('id')
                    record['id'] = table_unique_id
                    record['createdAt'] = int(table_json.get('createdAt'))
                    await table_queries.update_table(table_unique_id, json.dumps(record))
                else:
                    # Insert new table
                    await table_queries.insert_table(json.dumps(record))

                # insert attributes metadata
                if 'filed_list' in record and record['filed_list']:
                    table_unique_id = record['id']
                    for attirbute_record in record['filed_list']:
                        attribute_unique_id = str(uuid.uuid4())
                        current_timestamp = int(datetime.now().timestamp())
                        attirbute_record = {
                            'id': attribute_unique_id,
                            'tableId': table_unique_id,
                            'domainId': domain_unique_id,
                            'tenantUniqueId': tenant_unique_id,
                            'createdAt': current_timestamp,
                            'updatedAt': current_timestamp,
                            'updatedBy': service_account_name,
                            'deleted': False,
                            'tenantName': tenant_name,
                            'Table Description': record['Template Description'],
                            'Table Name': record['Template Name'],
                            **attirbute_record
                        }
                        existing_attribute = await attribute_queries.get_attribute_by_name_table_id_kba(
                            attirbute_record['Field Name'], attirbute_record['Product Domain'], table_unique_id, tenant_unique_id)
                        if existing_attribute:
                            # Update existing attribute
                            attribute_json = json.loads(existing_attribute[0]['metadata'])
                            attribute_unique_id = attribute_json.get('id')
                            attirbute_record['id'] = attribute_unique_id
                            attirbute_record['createdAt'] = int(attribute_json.get('createdAt'))
                            await attribute_queries.update_attribute(attribute_unique_id, json.dumps(attirbute_record))
                        else:
                            await attribute_queries.insert_attribute(json.dumps(attirbute_record))

    async def get_sheet_names(self, file_path: str):
        xls = pd.ExcelFile(file_path)
        return xls.sheet_names

    async def excel_to_data(self, file_path: str, target_sheet_name: str = None):
        # Read the Excel file using pandas
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names

        if target_sheet_name in sheet_names:
            matched_sheet = target_sheet_name
        else:
            pattern = re.compile(target_sheet_name, re.IGNORECASE)
            matching_sheets = [s for s in sheet_names if pattern.search(s)]
            if not matching_sheets:
                raise ValueError(f"No sheet found matching pattern: {target_sheet_name}")
            matched_sheet = matching_sheets[0]

        df = pd.read_excel(xls, sheet_name=matched_sheet, engine='openpyxl')
        df = df.fillna('')
        data = df.to_dict(orient='records')
        return data

    async def get_service_account_name(self):
        credentials, project_id = google.auth.default()
        service_account_email = credentials.service_account_email
        return service_account_email

    async def install_extension(self):
        return await data_access.install_extension()

    async def delete_attributes_metadata_by_domainId(self, domain_name):
        domain = await domain_queries.get_domain(domain_name)
        data_exist = json.loads(domain['domain_metadata'])
        domain_unique_id = data_exist.get('id')
        # delete attributes metadata
        await attribute_queries.delete_attributes_metadata_by_domainId(domain_unique_id)
        # delete tables metadata
        await table_queries.delete_tables_metadata_by_domainId(domain_unique_id)
        # delete tenants metadata
        await tenant_queries.delete_tenants_metadata_by_domainId(domain_unique_id)
        # delete domain metadata
        await domain_queries.delete_domain_metadata_by_domainId(domain_unique_id)
        return "Successfully"

    async def delete_attributes_metadata_by_tenant(self, tenant_id):
        # delete attributes metadata
        await attribute_queries.delete_attributes_metadata_by_tenant(tenant_id)
        # delete tables metadata
        await table_queries.delete_tables_metadata_by_tenant(tenant_id)
        # delete tenants metadata
        await tenant_queries.delete_tenants_metadata_by_tenant(tenant_id)
        return "Successfully"

    async def insert_glossary(self, key, file_name):
        try:
            # check key
            project_id = settings.project_id
            data_key = settings.data_key
            if key != data_key:
                return "Key not found"

            download_path = await self.download_glossary_file_from_gcp(project_id, file_name=f"glossary/{file_name}")
            glossary_excel_data = await self.excel_to_data(download_path, target_sheet_name='DataDict')
            if glossary_excel_data:
                await glossary_queries.remove_all_glossary()

            insert_count = 0
            for record in glossary_excel_data:
                record['id'] = str(uuid.uuid4())
                record['glossary_key'] = ':'.join([record['Tool'], record['Product'], record['Product Domain'], record['Template Name'], record['Field Name']])

                glossary_exist_one = await glossary_queries.get_glossary_by_key(record['glossary_key'])
                if glossary_exist_one is None:
                    await data_access.insert_glossary(json.dumps(record))
                    insert_count += 1
                else:
                    logger.info(f"Glossary already exists for key: {record['glossary_key']}, skipping insertion.")
            return {
                "total_excel_rows": len(glossary_excel_data),
                "inserted_rows": insert_count
            }
        except Exception as e:
            logger.error(f"Error inserting glossary data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
