"""
Native schema extraction for DISTILL.

Extracts common keys from array of objects, converts to tuples.
This provides the first compression layer by eliminating key repetition.

Layer 1: Schema Extraction
    Input:  [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    Output: schema=["age", "name"], tuples=[[30, "Alice"], [25, "Bob"]]
"""

from typing import Any, Dict, List, Tuple, Optional, Set


# Sentinel for missing values to distinguish from explicit None
class _Missing:
    """Sentinel class for missing dictionary keys.

    This distinguishes between a key that is absent from an object
    vs a key that is present with value None.
    """

    _instance = None

    def __new__(cls):
        # Singleton pattern for consistent identity checks
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<MISSING>"

    def __bool__(self) -> bool:
        return False


MISSING = _Missing()


def extract_schema(data: List[Any]) -> Tuple[List[str], List[List[Any]]]:
    """
    Extract schema from array of objects.

    Collects the union of all keys from all objects and converts each object
    into a tuple of values in consistent key order.

    Args:
        data: List of items (usually dictionaries)

    Returns:
        Tuple of (schema, tuples) where:
        - schema: List of field names in sorted order (for consistency)
        - tuples: List of value tuples matching schema order

    Edge Cases Handled:
        - Empty list: Returns ([], [])
        - List of empty dicts: Returns ([], [])
        - List of non-dicts: Returns ([], []) - caller should handle
        - Mixed list (dicts + non-dicts): Non-dicts become all-MISSING tuples
        - Inconsistent keys: Union schema with MISSING for absent keys

    Example:
        >>> extract_schema([{"name": "Alice", "age": 30}, {"name": "Bob"}])
        (["age", "name"], [[30, "Alice"], [MISSING, "Bob"]])
    """
    # Handle empty input
    if not data:
        return [], []

    # Collect all keys from all dict items
    all_keys = _get_union_schema(data)

    if not all_keys:
        # No keys found - either empty dicts or no dicts at all
        # Schema compression requires at least one key
        return [], []

    # Sort keys for consistent, deterministic ordering
    schema = sorted(all_keys)

    # Convert objects to tuples
    tuples = []
    for obj in data:
        if isinstance(obj, dict):
            # Use MISSING sentinel for keys that don't exist in this object
            tuple_values = [obj.get(field, MISSING) for field in schema]
            tuples.append(tuple_values)
        else:
            # Non-dict item in array - fill with MISSING
            # Note: This loses the original primitive value, which is acceptable
            # because compress.py validates that arrays contain dicts
            tuples.append([MISSING] * len(schema))

    return schema, tuples


def reconstruct_objects(schema: List[str], tuples: List[List[Any]]) -> List[Dict]:
    """
    Reconstruct objects from schema and tuples.

    Reverses extract_schema to rebuild the original dict objects.

    Args:
        schema: List of field names
        tuples: List of value tuples (length must match schema)

    Returns:
        List of reconstructed dictionaries

    Notes:
        - MISSING values are excluded from output (key absent)
        - None values are included (key present with null value)
        - Handles tuples shorter than schema (defensive)
    """
    if not schema or not tuples:
        return []

    objects = []
    for tuple_values in tuples:
        obj = {}
        for i, field in enumerate(schema):
            if i < len(tuple_values):
                value = tuple_values[i]
                # Only include non-MISSING values
                # MISSING means the key was absent, None means explicit null
                if not isinstance(value, _Missing):
                    obj[field] = value
        objects.append(obj)

    return objects


def find_array_data(data: Any) -> Tuple[Optional[str], List[Any], Optional[Dict]]:
    """
    Find compressible array data in nested structure.

    Searches for arrays of dictionaries that can be compressed using
    the schema extraction method. Preserves other data for lossless roundtrip.

    Args:
        data: Input data structure (dict, list, or primitive)

    Returns:
        Tuple of (wrapper_key, array_data, extra_data):
        - wrapper_key: Key name if array was in a dict, None if top-level list
        - array_data: The list to compress (may be empty if not compressible)
        - extra_data: Other dict keys to preserve (for lossless roundtrip)

    Heuristics:
        - Prefers larger arrays
        - Prefers arrays with more dict items (vs primitive arrays)
        - Returns empty array_data if no suitable array found

    Examples:
        >>> find_array_data([{"a": 1}, {"a": 2}])
        (None, [{"a": 1}, {"a": 2}], None)

        >>> find_array_data({"events": [{"a": 1}], "meta": {"count": 1}})
        ("events", [{"a": 1}], {"meta": {"count": 1}})

        >>> find_array_data({"x": 1, "y": 2})
        (None, [], None)  # No array to compress
    """
    # Case 1: Direct list input
    if isinstance(data, list):
        if not data:
            # Empty list - technically compressible but no benefit
            return None, [], None

        # Check if it contains at least one dict (suitable for schema compression)
        if any(isinstance(x, dict) for x in data):
            return None, data, None

        # List of primitives - not suitable for schema compression
        return None, [], None

    # Case 2: Dict containing arrays
    if isinstance(data, dict):
        if not data:
            # Empty dict
            return None, [], None

        # Find the best array candidate
        # Score based on: number of dict items in the array
        best_key: Optional[str] = None
        best_array: List[Any] = []
        best_score = 0

        for key, value in data.items():
            if isinstance(value, list) and value:
                # Count dict items (schema compression targets)
                dict_count = sum(1 for x in value if isinstance(x, dict))
                if dict_count > best_score:
                    best_score = dict_count
                    best_key = key
                    best_array = value

        if best_key is not None:
            # Found a suitable array
            extra = {k: v for k, v in data.items() if k != best_key}
            return best_key, best_array, extra if extra else None

    # Case 3: Primitive or other non-compressible type
    return None, [], None


def _get_union_schema(data: List[Any]) -> Set[str]:
    """
    Get union of all keys across all dict objects.

    Args:
        data: List that may contain dictionaries

    Returns:
        Set of all unique keys found in any dict

    Notes:
        - Skips non-dict items
        - Returns empty set if no dicts found
        - Keys are strings (as per JSON spec)
    """
    all_keys: Set[str] = set()
    for obj in data:
        if isinstance(obj, dict):
            all_keys.update(obj.keys())
    return all_keys


def validate_schema_data(data: List[Any]) -> bool:
    """
    Check if data is suitable for schema compression.

    Args:
        data: List to validate

    Returns:
        True if data can be schema-compressed, False otherwise

    Criteria:
        - Must be a non-empty list
        - Must contain at least one dict
        - At least one dict must have at least one key
    """
    if not isinstance(data, list) or not data:
        return False

    has_dict = False
    has_keys = False

    for item in data:
        if isinstance(item, dict):
            has_dict = True
            if item:  # Non-empty dict
                has_keys = True
                break

    return has_dict and has_keys
