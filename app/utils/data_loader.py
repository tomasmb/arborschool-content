"""Data loading utilities for standards and atoms files.

This module provides consistent loading functions that handle the polymorphic
JSON formats used in the project (both list and dict-with-metadata formats).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_file(path: Path | str) -> dict[str, Any] | list[Any]:
    """Load a JSON file with UTF-8 encoding.

    Args:
        path: Path to the JSON file.

    Returns:
        The parsed JSON content (dict or list).

    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json_file(
    data: Any,
    path: Path | str,
    ensure_ascii: bool = False,
    indent: int = 2,
) -> None:
    """Save data to a JSON file with consistent formatting.

    Args:
        data: The data to serialize.
        path: Output file path.
        ensure_ascii: If True, escape non-ASCII characters. Defaults to False.
        indent: Indentation level for pretty-printing. Defaults to 2.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)


def load_standards_file(path: Path | str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load a standards JSON file, handling both list and dict formats.

    The standards files can be either:
    - A list of standard dicts directly: [{"id": "M1-NUM-01", ...}, ...]
    - A dict with "standards" key: {"metadata": {...}, "standards": [...]}

    Args:
        path: Path to the standards JSON file.

    Returns:
        Tuple of (standards_list, metadata_dict).
        If the file is a plain list, metadata_dict will be empty.

    Example:
        >>> standards, metadata = load_standards_file("standards.json")
        >>> for std in standards:
        ...     print(std["id"])
    """
    data = load_json_file(path)

    if isinstance(data, list):
        return data, {}
    else:
        standards_list = data.get("standards", [])
        metadata = data.get("metadata", {})
        return standards_list, metadata


def load_atoms_file(path: Path | str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load an atoms JSON file, handling both list and dict formats.

    The atoms files can be either:
    - A list of atom dicts directly: [{"id": "A-M1-NUM-01-01", ...}, ...]
    - A dict with "atoms" key: {"metadata": {...}, "atoms": [...]}

    Args:
        path: Path to the atoms JSON file.

    Returns:
        Tuple of (atoms_list, metadata_dict).
        If the file is a plain list, metadata_dict will be empty.

    Example:
        >>> atoms, metadata = load_atoms_file("atoms.json")
        >>> for atom in atoms:
        ...     print(atom["id"])
    """
    data = load_json_file(path)

    if isinstance(data, list):
        return data, {}
    else:
        atoms_list = data.get("atoms", [])
        metadata = data.get("metadata", {})
        return atoms_list, metadata


def find_item_by_id(
    items: list[dict[str, Any]],
    item_id: str,
    id_field: str = "id",
) -> dict[str, Any] | None:
    """Find an item by its ID in a list of dicts.

    Args:
        items: List of dictionaries to search.
        item_id: The ID value to find.
        id_field: The field name containing the ID. Defaults to "id".

    Returns:
        The matching dict, or None if not found.

    Example:
        >>> standards = [{"id": "M1-NUM-01", "titulo": "..."}]
        >>> std = find_item_by_id(standards, "M1-NUM-01")
    """
    for item in items:
        if item.get(id_field) == item_id:
            return item
    return None


def find_items_by_ids(
    items: list[dict[str, Any]],
    item_ids: list[str],
    id_field: str = "id",
) -> dict[str, dict[str, Any]]:
    """Find multiple items by their IDs.

    Args:
        items: List of dictionaries to search.
        item_ids: List of ID values to find.
        id_field: The field name containing the ID. Defaults to "id".

    Returns:
        Dict mapping found IDs to their items.

    Example:
        >>> standards = [{"id": "M1-NUM-01"}, {"id": "M1-ALG-01"}]
        >>> found = find_items_by_ids(standards, ["M1-NUM-01", "M1-ALG-01"])
    """
    id_set = set(item_ids)
    result = {}
    for item in items:
        item_id = item.get(id_field)
        if item_id in id_set:
            result[item_id] = item
    return result
