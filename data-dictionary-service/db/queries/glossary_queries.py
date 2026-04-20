import json
import time

from core.config import get_logger
from db.session import db


logger = get_logger(__name__)


async def glossary_count_fields(glossary_key):
    query = """
        select * from count_fields($1)
    """
    try:
        logger.info(
            "start glossary_count_fields",
            extra={"function": "glossary_count_fields", "glossary_key": glossary_key},
        )

        rows = await db.fetch_jsonb(query, glossary_key)

        logger.info(
            "done glossary_count_fields",
            extra={
                "function": "glossary_count_fields",
                "rows": len(rows) if rows else 0,
            },
        )
        return rows
    except Exception:
        logger.error(
            "error glossary_count_fields",
            exc_info=True,
            extra={"function": "glossary_count_fields"},
        )
        raise


async def glossary_rollup_0(page: int, size: int, glossary_key: list, rollup: int):
    query = """
        select * from rollup_flat_fields($1, $2, $3)
    """
    try:
        logger.info(
            "start glossary_rollup_0",
            extra={
                "function": "glossary_rollup_0",
                "glossary_key": glossary_key,
                "page": page,
                "size": size,
            },
        )
        records = await db.fetch_jsonb(query, glossary_key, page, size)
        result = [
            {
                # "glossary_key": r["glossary_key"],
                "tool": r["tool"],
                "product": r["product"],
                "product_domain": r["product_domain"],
                "template_name": r["template_name"],
                "template_type": r["template_type"],
                "template_description": r["template_description"],
                "field_name": r["field_name"],
                "description": r["description"],
                "data_type": r["data_type"],
                "rule_type": r["rule_type"],
                "rules": r["rules"],
                "format": r["format"],
                "ai_enhanced_field_description": r["ai_enhanced_field_description"],
                "sample_data": r["sample_data"],
                "additional_field_description": r["additional_field_description"],
            }
            for r in records
        ]

        logger.info(
            "done glossary_rollup_0",
            extra={
                "function": "glossary_rollup_0",
                "rows": len(result) if result else 0,
            },
        )
        return result
    except Exception as e:
        logger.error(
            "error glossary_rollup_0",
            exc_info=True,
            extra={
                "function": "glossary_rollup_0",
                "page": page,
                "size": size,
            },
        )
        raise e


async def glossary_rollup_1(page: int, size: int, glossary_key: list, rollup: int):
    query = """
        select * from rollup_group_level1_paginated($1, $2, $3)
    """
    try:
        logger.info(
            "start glossary_rollup_1",
            extra={
                "function": "glossary_rollup_1",
                "glossary_key": glossary_key,
                "page": page,
                "size": size,
            },
        )
        records = await db.fetch_jsonb(query, glossary_key, page, size)
        result = [
            {
                "level1": r["level1"],
                "fields": json.loads(r["fields"]),
            }
            for r in records
        ]

        logger.info(
            "done glossary_rollup_1",
            extra={
                "function": "glossary_rollup_1",
                "rows": len(result) if result else 0,
            },
        )
        return result
    except Exception as e:
        logger.error(
            "error glossary_rollup_1",
            exc_info=True,
            extra={
                "function": "glossary_rollup_1",
                "page": page,
                "size": size,
            },
        )
        raise e


async def glossary_rollup_2(page: int, size: int, glossary_key: list, rollup: int):
    query = """
        select * from rollup_group_level2_paginated($1, $2, $3)
    """
    try:
        logger.info(
            "start glossary_rollup_2",
            extra={
                "function": "glossary_rollup_2",
                "glossary_key": glossary_key,
                "page": page,
                "size": size,
            },
        )

        records = await db.fetch_jsonb(query, glossary_key, page, size)
        result = [
            {
                "level2": r["level2"],
                "level2_children": json.loads(r["level1_children"]),
            }
            for r in records
        ]

        logger.info(
            "done glossary_rollup_2",
            extra={
                "function": "glossary_rollup_2",
                "rows": len(result) if result else 0,
            },
        )
        return result
    except Exception as e:
        logger.error(
            "error glossary_rollup_2",
            exc_info=True,
            extra={
                "function": "glossary_rollup_2",
                "page": page,
                "size": size,
            },
        )
        raise e


async def glossary_rollup_n(page: int, size: int, glossary_key: list, rollup: int):
    query = """
        select * from rollup_flat_fields($1, $2, $3)
    """
    try:
        logger.info(
            "start glossary_rollup_n",
            extra={
                "function": "glossary_rollup_n",
                "glossary_key": glossary_key,
                "page": page,
                "size": size,
            },
        )

        records = await db.fetch_jsonb(query, glossary_key, page, size)

        logger.info(
            "done glossary_rollup_n",
            extra={
                "function": "glossary_rollup_n",
                "rows": len(records) if records else 0,
            },
        )
        return records
    except Exception as e:
        logger.error(
            "error glossary_rollup_n",
            exc_info=True,
            extra={
                "function": "glossary_rollup_n",
                "page": page,
                "size": size,
            },
        )
        raise e


async def get_glossary_by_key(key: str):
    query = """
        select * from glossary where lower(glossary_key) = lower($1)
    """
    return await db.fetch_one(query, key)


async def remove_all_glossary():
    query = """
        TRUNCATE TABLE glossary;
    """
    return await db.execute(query)
