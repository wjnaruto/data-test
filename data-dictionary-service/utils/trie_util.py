from typing import Any, Dict, List, Optional
from collections import defaultdict


_FIELDS_KEY = "__fields__"


class TrieNode:
    __slots__ = ("children", "fields", "depth_to_leaf")

    def __init__(self, field_info: Optional[Dict[str, Any]] = None) -> None:
        self.children = defaultdict(TrieNode)
        self.fields: List[Dict[str, Any]] = []
        self.depth_to_leaf: int = 0
        if field_info:
            self.fields.append(field_info)


class Trie:

    def __init__(self) -> None:
        self.root = TrieNode()

    def insert_path(self, tokens: List[str]) -> TrieNode:
        if not isinstance(tokens, list):
            raise TypeError("tokens must be a list")
        l = len(tokens)
        node = self.root
        d = 0
        for tok in tokens:
            node = node.children[tok]
            if node.depth_to_leaf < d:
                node.depth_to_leaf = d
            d += 1
        return node

    def add_field(self, node: TrieNode, field_info: Dict[str, Any]) -> None:
        node.fields.append(field_info)
