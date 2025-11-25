"""
Dictionary encoding for DISTILL.

Maps frequent values to single lowercase letter codes (a-z).
This provides the second compression layer after schema extraction.
"""

from typing import Any, Dict, List, Set, Tuple, Optional
from collections import Counter
import string
import json


# We need to handle the MISSING sentinel if it's passed here
try:
    from .schema import MISSING, _Missing
except ImportError:
    # Fallback if schema not fully set up yet or circular import
    class _Missing:
        pass
    MISSING = _Missing()


def flatten_nested_value(value: Any) -> str:
    """
    Flatten a nested value to a string representation for encoding.

    Uses JSON serialization for ALL types to ensure lossless roundtrip.
    This guarantees type preservation: string "123" stays distinct from int 123.

    Args:
        value: Any JSON-compatible value

    Returns:
        JSON-serialized string that can be reversed via unflatten_value

    Type Preservation (via JSON):
        - None -> "null"
        - True -> "true", False -> "false"
        - Numbers -> "123", "3.14" (unquoted in JSON)
        - Strings -> '"hello"' (quoted in JSON - this preserves type!)
        - Objects/Arrays -> '{"key":"value"}', '[1,2,3]'
        - MISSING -> "\u0000MISSING" (Special sentinel)

    Example:
        >>> flatten_nested_value("123")  # String
        '"123"'
        >>> flatten_nested_value(123)    # Integer
        '123'
    """
    if isinstance(value, _Missing):
        return "\u0000MISSING"  # Special sentinel for missing values

    # Use JSON dumps for everything to preserve types
    # This means strings get quotes: "hello" -> '"hello"'
    # Numbers stay raw: 123 -> '123'
    # This is the KEY to lossless compression
    return json.dumps(value, separators=(',', ':'), sort_keys=True)


def unflatten_value(value_str: str) -> Any:
    """
    Unflatten a JSON string representation back to original value.

    Reverses flatten_nested_value to restore original types exactly.

    Args:
        value_str: JSON string from flatten_nested_value

    Returns:
        Restored value with exact original type

    Example:
        >>> unflatten_value('"123"')  # JSON string
        '123'
        >>> unflatten_value('123')    # JSON number
        123
    """
    if value_str == "\u0000MISSING":
        return MISSING

    if value_str == "":
        return None  # Legacy/Fallback

    # Parse JSON to restore exact type
    try:
        return json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        # If not valid JSON, return as raw string
        # This handles legacy data or edge cases
        return value_str


class DictionaryEncoder:
    """
    Creates compact dictionary mapping values to single-letter codes.

    Assigns codes by frequency (most frequent = 'a', second = 'b', etc.).
    Maximum 26 unique values can be encoded (a-z).

    Example:
        encoder = DictionaryEncoder()
        encoder.build_dictionary(["click", "click", "home", "mobile"])
        # Result: {"a": "click", "b": "home", "c": "mobile"}
    """

    def __init__(self, min_frequency: int = 1):
        """
        Initialize the dictionary encoder.

        Args:
            min_frequency: Minimum occurrences to include in dictionary (default 1)
        """
        self.min_frequency = min_frequency
        self.dictionary: Dict[str, str] = {}  # code -> value
        self.reverse_dict: Dict[str, str] = {}  # value -> code
        self._used_codes: Set[str] = set()

    def build_dictionary(self, values: List[Any]) -> Dict[str, str]:
        """
        Build dictionary from list of values.

        Assigns codes by frequency (most frequent = 'a').

        Args:
            values: All values from tuples (can include nested structures)

        Returns:
            Dictionary mapping single-letter codes to values

        Notes:
            - Filters values by min_frequency
            - Skips single-character values (no compression benefit)
            - Maximum 26 codes (a-z)
            - Stable sorting by frequency desc, then alphabetically
        """
        # Flatten all values to strings for counting
        flattened = [flatten_nested_value(v) for v in values]

        # Count frequencies
        freq = Counter(flattened)

        # Filter by minimum frequency
        freq = {v: c for v, c in freq.items() if c >= self.min_frequency}

        # Sort by frequency descending, then alphabetically for stability
        sorted_values = sorted(freq.items(), key=lambda x: (-x[1], x[0]))

        # Assign codes a-z
        available_codes = list(string.ascii_lowercase)

        self.dictionary = {}
        self.reverse_dict = {}
        self._used_codes = set()

        for value, count in sorted_values:
            if not available_codes:
                break  # Ran out of codes (26 max)

            # Skip very short values that wouldn't benefit from encoding
            # Single characters don't gain anything
            if len(value) <= 1:
                continue

            code = available_codes.pop(0)
            self.dictionary[code] = value
            self.reverse_dict[value] = code
            self._used_codes.add(code)

        return self.dictionary

    def get_reverse_dictionary(self) -> Dict[str, str]:
        """Get value -> code mapping for encoding."""
        return self.reverse_dict

    def encode_value(self, value: Any) -> str:
        """
        Encode single value to its code, or return flattened value if not in dict.

        Args:
            value: Any JSON-compatible value

        Returns:
            Single-letter code if in dictionary, otherwise flattened string
        """
        flat_val = flatten_nested_value(value)
        return self.reverse_dict.get(flat_val, flat_val)

    def decode_value(self, code: str) -> Any:
        """
        Decode a code back to its original value.

        Args:
            code: Single-letter code or original flattened value

        Returns:
            Original value (unflattened if it was a complex type)
        """
        if code in self.dictionary:
            flat_val = self.dictionary[code]
            return unflatten_value(flat_val)
        return unflatten_value(code)

    def encode_tuple(self, tuple_values: List[Any]) -> str:
        """
        Encode tuple of values to concatenated codes.

        If all values encode to single letters, concatenates them.
        Otherwise, uses comma-separated format with escape handling.

        Args:
            tuple_values: List of values from one record

        Returns:
            Encoded string like "abc" or "a,longer_value,b"

        Example:
            ["click", "home", "mobile"] -> "abc" (if all in dict)
            ["click", "some long text", "mobile"] -> "a,some long text,c"
        """
        codes = [self.encode_value(v) for v in tuple_values]

        # Check if ALL values are in dictionary (can use concatenation)
        # This avoids ambiguity between code "a" and literal "a"
        all_are_codes = True
        for val in tuple_values:
            flat = flatten_nested_value(val)
            if flat not in self.reverse_dict:
                all_are_codes = False
                break

        if all_are_codes and all(len(c) == 1 for c in codes):
            return ''.join(codes)

        # Fallback: comma-separated with escaping
        escaped = []
        for c in codes:
            # Escape commas and backslashes in values
            if ',' in c or '\\' in c:
                c = c.replace('\\', '\\\\').replace(',', '\\,')
            escaped.append(c)
        return ','.join(escaped)

    def decode_tuple(self, encoded: str, schema_length: int) -> List[Any]:
        """
        Decode concatenated codes back to values.

        Args:
            encoded: Concatenated codes like "abc" or comma-separated
            schema_length: Expected number of fields

        Returns:
            List of decoded values
        """
        # Check if it's concatenated single-letter codes
        # Must match schema length AND all chars must be lowercase letters
        if (len(encoded) == schema_length and
                all(c in string.ascii_lowercase for c in encoded)):
            return [self.decode_value(c) for c in encoded]

        # Parse comma-separated format with escape handling
        parts = self._split_escaped(encoded)
        return [self.decode_value(p) for p in parts]

    def _split_escaped(self, s: str) -> List[str]:
        """
        Split comma-separated string handling escaped commas.

        Args:
            s: String with possible escaped commas (\\,)

        Returns:
            List of parts with escapes resolved
        """
        parts = []
        current = []
        i = 0

        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                # Escaped character - include the next char literally
                current.append(s[i + 1])
                i += 2
            elif s[i] == ',':
                parts.append(''.join(current))
                current = []
                i += 1
            else:
                current.append(s[i])
                i += 1

        parts.append(''.join(current))
        return parts

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the dictionary.

        Returns:
            Dictionary with encoding statistics
        """
        return {
            "codes_used": len(self.dictionary),
            "codes_available": 26 - len(self.dictionary),
            "avg_value_length": (
                sum(len(v) for v in self.dictionary.values()) / len(self.dictionary)
                if self.dictionary else 0
            )
        }


# Convenience functions

def build_codebook(data: Any, min_frequency: int = 1) -> Dict[str, str]:
    """
    Build dictionary codebook from data.

    Convenience function for direct use without instantiating DictionaryEncoder.

    Args:
        data: JSON-compatible data structure
        min_frequency: Minimum occurrences to create a code

    Returns:
        Dictionary mapping codes to values
    """
    encoder = DictionaryEncoder(min_frequency=min_frequency)
    values = _collect_values(data)
    return encoder.build_dictionary(values)


def _collect_values(data: Any) -> List[Any]:
    """
    Recursively collect all leaf values from data structure.

    Args:
        data: JSON-compatible data structure

    Returns:
        List of all leaf values (non-None, non-container)
    """
    values: List[Any] = []

    def _collect(d: Any) -> None:
        if isinstance(d, dict):
            for v in d.values():
                _collect(v)
        elif isinstance(d, list):
            for item in d:
                _collect(item)
        elif d is not None:
            values.append(d)

    _collect(data)
    return values


# Legacy function for backward compatibility

def apply_huffman(
    data: Any,
    prev_output: Optional[str] = None,
    min_frequency: int = 1,
    min_length: int = 2
) -> Tuple[str, Dict]:
    """
    Legacy function - creates dictionary encoder and builds codebook.

    Maintained for backward compatibility but internal format has changed.

    Args:
        data: JSON-compatible data structure
        prev_output: Unused (kept for compatibility)
        min_frequency: Minimum occurrences to create a code
        min_length: Unused (kept for compatibility)

    Returns:
        Tuple of (empty string, dict with dictionary and codes_created)
    """
    encoder = DictionaryEncoder(min_frequency=min_frequency)
    values = _collect_values(data)
    dictionary = encoder.build_dictionary(values)

    return "", {
        "dictionary": dictionary,
        "codes_created": len(dictionary)
    }
