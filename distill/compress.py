"""
Main compression module for DISTILL.

Three-layer compression architecture:
    Layer 1: Schema Extraction - Extract field schema, convert objects to tuples
    Layer 2: Dictionary Encoding - Map frequent values to single-letter codes (a-z)
    Layer 3: Equivalence Partitioning - Group repeated tuples into #N references

Output format:
{
    "$": {
        "schema": ["field1", "field2", ...],
        "dict": {"a": "value1", "b": "value2", ...},
        "equiv": {"#0": "abc", "#1": "xyz", ...}
    },
    "dataKey": ["#0", "abd", "#0", ...]
}
"""

from typing import Any, Dict, List, Literal, Optional, Tuple, Union
import json
import math

from .core.schema import extract_schema, find_array_data, MISSING
from .core.huffman import DictionaryEncoder
from .core.equivalence import EquivalencePartitioner
from .core.tokenizer import count_tokens
from .exceptions import CompressionError, ValidationError, InvalidInputError
from .config import get_config


CompressionLevel = Literal["low", "medium", "high", "auto"]


def _validate_input(data: Any) -> None:
    """
    Validate input data is JSON-compatible.

    Args:
        data: Input data to validate

    Raises:
        InvalidInputError: If data is None or empty string
        ValidationError: If data contains non-JSON-compatible values
    """
    config = get_config()

    if data is None:
        raise InvalidInputError(
            "Input data cannot be None. "
            "Provide a valid JSON-compatible data structure (dict, list, str, int, float, bool)."
        )

    if isinstance(data, str):
        if data.strip() == "":
            raise InvalidInputError(
                "Input string cannot be empty. "
                "Provide a valid JSON string or non-empty data structure."
            )
        # If it's a string, we assume it's valid JSON (will be parsed later)
        return

    # Check for non-JSON-compatible values
    # We use a recursive check but limit depth to avoid stack overflow on deep structures
    
    def check_value(v: Any, path: str = "root", depth: int = 0) -> None:
        if depth > config.max_depth:
            raise ValidationError(f"Max nesting depth exceeded at {path} (limit: {config.max_depth})")
            
        if isinstance(v, float):
            if math.isnan(v):
                raise ValidationError(
                    f"NaN value found at {path}. "
                    "NaN is not valid JSON. Replace with null or a valid number."
                )
            if math.isinf(v):
                raise ValidationError(
                    f"Infinity value found at {path}. "
                    "Infinity is not valid JSON. Replace with a large finite number or null."
                )
        elif isinstance(v, dict):
            for k, val in v.items():
                if not isinstance(k, str):
                     raise ValidationError(f"Dict keys must be strings at {path}")
                check_value(val, f"{path}.{k}", depth + 1)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                check_value(item, f"{path}[{i}]", depth + 1)
        elif isinstance(v, set):
            raise ValidationError(
                f"Set found at {path}. "
                "Sets are not JSON-compatible. Convert to a list."
            )
        elif isinstance(v, (str, int, bool, type(None))):
            pass
        else:
            raise ValidationError(
                f"Non-JSON-compatible type {type(v).__name__} found at {path}. "
                "Only dict, list, str, int, float, bool, and None are allowed."
            )

    check_value(data)


def compress(
    data: Any,
    level: CompressionLevel = "auto"
) -> Dict[str, Any]:
    """
    Compress JSON data using DISTILL format.

    DISTILL - Data Intelligent Structure Token-efficient Interchange for LLMs

    Three-layer compression:
        1. Schema Extraction: Objects -> Tuples + Schema
        2. Dictionary Encoding: Values -> Single-letter codes (a-z)
        3. Equivalence Partitioning: Repeated tuples -> #N references

    Args:
        data: JSON-compatible data structure (dict, list, or JSON string)
        level: Compression level (currently uses optimal settings regardless)

    Returns:
        Dictionary with:
            - "compressed": The compressed JSON string
            - "meta": Metadata about the compression

    Raises:
        InvalidInputError: If data is None or empty string
        ValidationError: If data contains non-JSON-compatible values (NaN, Inf, sets)
        CompressionError: If compression fails for other reasons
    """
    config = get_config()

    # Validate input
    _validate_input(data)

    # Parse JSON string if needed
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise InvalidInputError(
                f"Invalid JSON string: {e}. "
                "Ensure the input is valid JSON with double quotes for strings."
            )

    # Validate parsed data again
    _validate_input(data)

    # Get original token count
    original_json = json.dumps(data, separators=(',', ':'))
    original_tokens = count_tokens(original_json)

    # Find array data to compress
    wrapper_key, array_data, extra_data = find_array_data(data)

    if not array_data:
        # No compressible array found, return as-is
        return {
            "compressed": original_json,
            "meta": {
                "method": "passthrough",
                "reason": "no array of objects found",
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "reduction_percent": 0,
                "schema_fields": 0,
                "dict_codes": 0,
                "equiv_classes": 0
            }
        }

    try:
        # =========================================
        # Layer 1: Schema Extraction
        # =========================================
        schema, tuples = extract_schema(array_data)

        if not schema:
            return {
                "compressed": original_json,
                "meta": {
                    "method": "passthrough",
                    "reason": "no schema extractable",
                    "original_tokens": original_tokens,
                    "compressed_tokens": original_tokens,
                    "reduction_percent": 0,
                    "schema_fields": 0,
                    "dict_codes": 0,
                    "equiv_classes": 0
                }
            }

        # =========================================
        # Layer 2: Dictionary Encoding
        # =========================================
        encoder = DictionaryEncoder(min_frequency=config.dict_min_frequency)

        # Collect all values for dictionary building
        all_values = []
        for tuple_vals in tuples:
            all_values.extend(tuple_vals)

        dictionary = encoder.build_dictionary(all_values)

        # Encode all tuples
        encoded_tuples = [encoder.encode_tuple(t) for t in tuples]

        # =========================================
        # Layer 3: Equivalence Partitioning
        # =========================================
        partitioner = EquivalencePartitioner(min_occurrences=config.min_equiv_count)
        equivalences, final_data = partitioner.find_equivalences(encoded_tuples)

        # =========================================
        # Build Output Structure
        # =========================================
        meta_section: Dict[str, Any] = {}

        # Always include schema
        meta_section["schema"] = schema

        # Include dictionary if any codes were created
        if dictionary:
            meta_section["dict"] = dictionary

        # Include equivalences if any were found
        if equivalences:
            meta_section["equiv"] = equivalences

        # Determine data key (use original key or "data")
        data_key = wrapper_key or "data"

        # Track if original was a bare list (no wrapper)
        is_bare_list = wrapper_key is None

        output: Dict[str, Any] = {
            "$": meta_section,
            data_key: final_data
        }

        # Mark if original was bare list for proper decompression
        if is_bare_list:
            output["$"]["_bare"] = True

        # Add extra data if present (preserved from original structure)
        if extra_data:
            output["_extra"] = extra_data

        # Serialize to JSON
        compressed_json = json.dumps(output, separators=(',', ':'))
        compressed_tokens = count_tokens(compressed_json)

        # Calculate reduction
        reduction = ((original_tokens - compressed_tokens) / original_tokens * 100) if original_tokens > 0 else 0

        # Check if compression actually reduced size
        if config.fallback_on_increase and compressed_tokens >= original_tokens:
            return {
                "compressed": original_json,
                "meta": {
                    "method": "fallback",
                    "reason": "compression would increase size",
                    "original_tokens": original_tokens,
                    "compressed_tokens": original_tokens,
                    "reduction_percent": 0,
                    "fallback": True,
                    "attempted_tokens": compressed_tokens,
                    "schema_fields": len(schema),
                    "dict_codes": len(dictionary),
                    "equiv_classes": len(equivalences)
                }
            }

        return {
            "compressed": compressed_json,
            "meta": {
                "method": "schema+dict+equiv",
                "original_tokens": original_tokens,
                "compressed_tokens": compressed_tokens,
                "reduction_percent": round(reduction, 1),
                "tokens_saved": original_tokens - compressed_tokens,
                "schema_fields": len(schema),
                "dict_codes": len(dictionary),
                "equiv_classes": len(equivalences),
                "data_key": data_key,
                "has_extra": extra_data is not None
            }
        }

    except Exception as e:
        raise CompressionError(
            f"Compression failed: {e}. "
            "This may be due to unsupported data structure or internal error."
        ) from e


def compress_to_string(data: Any, level: CompressionLevel = "auto") -> str:
    """
    Compress data and return just the compressed string.

    Convenience function that discards metadata.

    Args:
        data: JSON-compatible data structure
        level: Compression level

    Returns:
        Compressed JSON string
    """
    result = compress(data, level)
    return result["compressed"]


def analyze(data: Any) -> Dict[str, Any]:
    """
    Analyze data for compression potential without compressing.

    Args:
        data: JSON-compatible data structure

    Returns:
        Dictionary with analysis results
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return {"compressible": False, "reason": "Invalid JSON string"}

    original_json = json.dumps(data, separators=(',', ':'))
    original_tokens = count_tokens(original_json)

    wrapper_key, array_data, extra_data = find_array_data(data)

    if not array_data:
        return {
            "original_tokens": original_tokens,
            "compressible": False,
            "reason": "no array of objects found"
        }

    schema, tuples = extract_schema(array_data)

    if not schema:
        return {
            "original_tokens": original_tokens,
            "compressible": False,
            "reason": "no schema extractable"
        }

    # Count unique values
    all_values = []
    for t in tuples:
        all_values.extend(t)
    
    # Use string representation for counting unique values
    unique_values = len(set(str(v) for v in all_values if not isinstance(v, type(MISSING))))

    # Count repeated tuples
    # We need a hashable representation of tuples
    tuple_strs = [str(t) for t in tuples]
    from collections import Counter
    tuple_counts = Counter(tuple_strs)
    repeated = sum(1 for count in tuple_counts.values() if count >= 2)

    # Estimate reduction
    # Very rough estimate
    estimated_reduction = min(50, (len(schema) * 5) + (repeated * 10) + (26 - min(26, unique_values)) * 2)

    return {
        "original_tokens": original_tokens,
        "compressible": True,
        "schema_fields": len(schema),
        "total_tuples": len(tuples),
        "unique_values": unique_values,
        "repeated_tuples": repeated,
        "estimated_reduction": estimated_reduction,
        "data_key": wrapper_key or "data"
    }
