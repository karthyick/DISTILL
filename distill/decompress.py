"""
Decompression module for DISTILL.

Reconstructs original JSON from compressed DISTILL output.
Ensures 100% lossless roundtrip with the compress function.

Input format:
{
    "$": {
        "schema": ["field1", "field2", ...],
        "dict": {"a": "value1", "b": "value2", ...},
        "equiv": {"#0": "abc", "#1": "xyz", ...}
    },
    "dataKey": ["#0", "abd", "#0", ...]
}
"""

from typing import Any, Dict, List, Optional, Union
import json

from .exceptions import DecompressionError
from .core.schema import reconstruct_objects
from .core.huffman import DictionaryEncoder
from .core.equivalence import EquivalencePartitioner


class Decompressor:
    """
    Decompresses DISTILL output back to original JSON structure.

    Three-layer decompression (reverse order):
        1. Expand equivalence references (#N -> encoded tuple)
        2. Decode dictionary codes (abc -> original values)
        3. Apply schema (tuple -> object with field names)
    """

    def __init__(self):
        """Initialize the decompressor."""
        self.schema: List[str] = []
        self.dictionary: Dict[str, str] = {}  # code -> value
        self.equivalences: Dict[str, str] = {}  # "#N" -> encoded tuple
        self.data_key: Optional[str] = None
        self.extra_data: Optional[Dict] = None

    def decompress(self, compressed: Union[str, Dict[str, Any]]) -> Any:
        """
        Decompress DISTILL output to original JSON.

        Args:
            compressed: DISTILL compressed JSON string or parsed dictionary

        Returns:
            Original JSON-compatible data structure

        Raises:
            DecompressionError: If decompression fails
        """
        data = compressed

        # Parse string if needed
        if isinstance(data, str):
            if not data.strip():
                raise DecompressionError("Invalid compressed input: must be a non-empty string")
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise DecompressionError(f"Invalid JSON: {e}")

        # Handle non-dict data (passthrough from compress)
        # Lists, primitives, etc. that weren't compressed are returned as-is
        if not isinstance(data, dict):
            # Not DISTILL format - return as-is (this is valid for passthrough)
            return data

        # Check if it's DISTILL format (has "$" metadata section)
        if "$" not in data:
            # Not DISTILL format, return as-is (passthrough case)
            return data

        # Reset state
        self._reset()

        # Extract metadata from "$" section
        meta = data["$"]

        if not isinstance(meta, dict):
            raise DecompressionError("Invalid metadata section: '$' must be an object")

        # Get schema (required)
        self.schema = meta.get("schema", [])
        if not isinstance(self.schema, list):
             raise DecompressionError("Invalid schema: must be a list")

        # Get dictionary (optional)
        self.dictionary = meta.get("dict", {})

        # Get equivalences (optional)
        self.equivalences = meta.get("equiv", {})

        # Get extra data (optional)
        self.extra_data = data.get("_extra")

        # Find the data key (not "$" or "_extra")
        encoded_data = None
        for key, value in data.items():
            if key not in ("$", "_extra"):
                if isinstance(value, list):
                    self.data_key = key
                    encoded_data = value
                    break

        if encoded_data is None:
            raise DecompressionError("No data array found in compressed format")

        # =========================================
        # Layer 1: Expand equivalence references
        # =========================================
        partitioner = EquivalencePartitioner()
        partitioner.set_equivalences(self.equivalences)
        expanded_data = partitioner.expand_equivalences(encoded_data)

        # =========================================
        # Layer 2: Decode dictionary codes
        # =========================================
        encoder = DictionaryEncoder()
        encoder.dictionary = self.dictionary
        
        decoded_tuples = []
        schema_length = len(self.schema)
        
        for item in expanded_data:
            if not isinstance(item, str):
                 # Should be string if encoded
                 raise DecompressionError(f"Unexpected data type in encoded array: {type(item)}")
            
            decoded_tuples.append(encoder.decode_tuple(item, schema_length))

        # =========================================
        # Layer 3: Apply schema to reconstruct objects
        # =========================================
        records = reconstruct_objects(self.schema, decoded_tuples)

        # Check if original was a bare list
        is_bare_list = meta.get("_bare", False)

        # Build result structure
        if is_bare_list:
            # Original was a bare list, return list directly
            result = records
        else:
            # Original was wrapped in dict
            result = {self.data_key: records}

            # Merge extra data if present
            if self.extra_data and isinstance(self.extra_data, dict):
                result.update(self.extra_data)

        return result

    def _reset(self) -> None:
        """Reset internal state."""
        self.schema = []
        self.dictionary = {}
        self.equivalences = {}
        self.data_key = None
        self.extra_data = None


def decompress(compressed: Union[str, Dict[str, Any]]) -> Any:
    """
    Decompress DISTILL output back to original JSON.

    Args:
        compressed: DISTILL compressed string, or result dict from compress()

    Returns:
        Original JSON-compatible data structure

    Raises:
        DecompressionError: If decompression fails

    Examples:
        >>> from distill import compress, decompress
        >>> original = {"events": [{"type": "click", "page": "home"}]}
        >>> result = compress(original)
        >>> restored = decompress(result["compressed"])
        >>> # or
        >>> restored = decompress(result)  # Pass the whole result dict
    """
    # Validate input type first
    if compressed is None:
        raise DecompressionError("Invalid input: None is not valid compressed data")

    # Handle result dict from compress()
    if isinstance(compressed, dict) and "compressed" in compressed:
        compressed = compressed["compressed"]

    # Type validation - only strings and dicts are valid inputs
    # (lists/primitives from passthrough will come as JSON strings)
    if not isinstance(compressed, (str, dict)):
        raise DecompressionError(
            f"Invalid input type: expected string or dict, got {type(compressed).__name__}"
        )

    decompressor = Decompressor()
    return decompressor.decompress(compressed)


def is_distill_format(text: Union[str, Dict]) -> bool:
    """
    Check if input is in DISTILL compressed format.

    Args:
        text: String or dict to check

    Returns:
        True if text is DISTILL format (JSON with "$" metadata)
    """
    if isinstance(text, dict):
        return "$" in text and isinstance(text["$"], dict) and "schema" in text["$"]

    if not text or not isinstance(text, str):
        return False

    text = text.strip()
    
    # Quick check before parsing
    if '"$":' not in text:
        return False

    # Must be valid JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False

    # Must be a dict with "$" key
    if not isinstance(data, dict) or "$" not in data:
        return False

    # "$" must contain schema
    meta = data.get("$")
    if not isinstance(meta, dict) or "schema" not in meta:
        return False

    return True
