from typing import List, Any, Dict
from fastapi import HTTPException
from core.config import get_logger
from db.queries import glossary_queries
from core.constants import RollupLevel
from utils.trie_util import Trie, TrieNode


logger = get_logger(__name__)


class GlossaryService:

    async def glossary_by_key(self, page: int, size: int, glossary_key: list, rollup: int):
        try:
            total_row = await glossary_queries.glossary_count_fields(glossary_key)
            total = total_row[0]["count_fields"]
            if rollup == RollupLevel.FIELD:
                # If rollup is 0, fetch records by key without any grouping
                result = await glossary_queries.glossary_rollup_0(page, size, glossary_key, rollup)
            elif rollup == RollupLevel.TEMPLATE:
                # If rollup is 1, fetch records with rollup level 1 and group by template
                result = await glossary_queries.glossary_rollup_1(page, size, glossary_key, rollup)
            elif rollup == RollupLevel.PRODUCT_DOMAIN:
                # If rollup is 2, fetch records with rollup level 2 and group by product domain
                result = await glossary_queries.glossary_rollup_2(page, size, glossary_key, rollup)
            else:
                # Default case, fetch records by key
                records = await glossary_queries.glossary_rollup_n(page, size, glossary_key, rollup)
                result = self.build_nested(records, rollup)

            return {
                "total": total,
                "page": page,
                "size": size,
                "glossaries": result
            }

        except Exception as e:
            logger.error(f"Error fetching GLossary data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def build_nested(self, records, rollup: int):
        """
        Build a nested structure from the records based on the rollup level.
        """
        trie = Trie()
        for rec in records:
            levels: List[str] = rec.get("levels", [])
            if not isinstance(levels, list):
                continue
            depth = len(levels)
            if depth <= 1:
                continue

            start_index = depth - 1 - rollup
            if start_index < 0:
                start_index = 0
            relevant_levels = levels[start_index: depth - 1]
            if not relevant_levels:
                continue

            fname = rec.get("field_name")
            if not fname:
                continue

            end_node = trie.insert_path(relevant_levels)
            trie.add_field(end_node,
                           field_info= {
                               "template_type": rec.get("template_type"),
                               "template_description": rec.get("template_description"),
                               "field_name": fname,
                               "description": rec.get("description"),
                               "data_type": rec.get("data_type"),
                               "rule_type": rec.get("data_type"),
                               "rules": rec.get("rules"),
                               "format": rec.get("format"),
                               "ai_enhanced_field_description": rec.get("ai_enhanced_field_description"),
                               "sample_data": rec.get("sample_data"),
                               "additional_field_description": rec.get("additional_field_description")
                               })

        return self._trie_to_nested_by_leaf_depth(trie.root)

    def _trie_to_nested_by_leaf_depth(self, node: TrieNode):
        result = []
        for level_value, child in node.children.items():
            depth_from_leaf = child.depth_to_leaf
            level_key = f"level{depth_from_leaf}"
            child_key = "fields" if depth_from_leaf == 1 else f"{level_key}_children"

            children = []
            if child.children:
                children.extend(self._trie_to_nested_by_leaf_depth(child))
            if child.fields:
                children.extend(child.fields)

            result.append({level_key: level_value, child_key: children})
        return result
