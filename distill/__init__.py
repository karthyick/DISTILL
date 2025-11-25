"""
DISTILL - Data Intelligent Structure Token-efficient Interchange for LLMs

A Python package that compresses JSON data for LLM consumption while
maintaining semantic readability. Unlike binary compression (gzip, LZ77),
DISTILL preserves meaning while reducing token count.

Three-Layer Compression Architecture:
    1. Schema Extraction: Objects -> Tuples + Schema
    2. Dictionary Encoding: Values -> Single-letter codes (a-z)
    3. Equivalence Partitioning: Repeated tuples -> #N references

Output Format:
    {
        "$": {
            "schema": ["field1", "field2"],
            "dict": {"a": "value1", "b": "value2"},
            "equiv": {"#0": "ab"}
        },
        "dataKey": ["#0", "cd", "#0"]
    }

Basic Usage:
    >>> from distill import compress, decompress
    >>>
    >>> data = {
    ...     "users": [
    ...         {"name": "Alice", "role": "admin"},
    ...         {"name": "Bob", "role": "admin"},
    ...         {"name": "Charlie", "role": "viewer"}
    ...     ]
    ... }
    >>>
    >>> # Compress
    >>> result = compress(data)
    >>> print(result["compressed"])
    >>> print(f"Reduced by {result['meta']['reduction_percent']}%")
    >>>
    >>> # Decompress back to original
    >>> original = decompress(result["compressed"])

Author: KR
License: MIT
"""

__version__ = "0.2.0"
__author__ = "KR"

from .compress import compress, analyze, CompressionLevel
from .decompress import decompress, Decompressor, is_distill_format
from .utils import (
    validate_json,
    parse_json,
    pretty_print,
    estimate_cost_savings,
    analyze_data
)
from .core.tokenizer import count_tokens, get_token_stats, is_tiktoken_available

# Configuration
from .config import (
    DistillConfig,
    get_config,
    configure,
    reset_config,
    with_config
)

# Exceptions
from .exceptions import (
    DistillError,
    CompressionError,
    DecompressionError,
    ValidationError,
    CircularReferenceError,
    MaxDepthExceededError,
    MaxSizeExceededError,
    InvalidInputError,
    SchemaExtractionError,
    DictionaryOverflowError
)

# File I/O
from .io import (
    DistillIO,
    compress_file,
    decompress_file,
    batch_compress,
    stream_json_array
)

__all__ = [
    # Main functions
    "compress",
    "decompress",
    "analyze",

    # Classes
    "Decompressor",

    # Utilities
    "is_distill_format",
    "validate_json",
    "parse_json",
    "pretty_print",
    "estimate_cost_savings",
    "analyze_data",

    # Token utilities
    "count_tokens",
    "get_token_stats",
    "is_tiktoken_available",

    # Configuration
    "DistillConfig",
    "get_config",
    "configure",
    "reset_config",
    "with_config",

    # Exceptions
    "DistillError",
    "CompressionError",
    "DecompressionError",
    "ValidationError",
    "CircularReferenceError",
    "MaxDepthExceededError",
    "MaxSizeExceededError",
    "InvalidInputError",
    "SchemaExtractionError",
    "DictionaryOverflowError",

    # File I/O
    "DistillIO",
    "compress_file",
    "decompress_file",
    "batch_compress",
    "stream_json_array",

    # Type hints
    "CompressionLevel",

    # Metadata
    "__version__",
    "__author__",
]
