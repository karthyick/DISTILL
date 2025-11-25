"""
DISTILL Core Modules.

Contains the core compression algorithms:
- schema: Native schema extraction (objects -> tuples)
- huffman: Dictionary encoding (values -> a-z codes)
- equivalence: Equivalence partitioning (repeated tuples -> #N refs)
- tokenizer: Token counting utility
"""

from .tokenizer import count_tokens, get_token_stats, is_tiktoken_available
from .schema import extract_schema, find_array_data, reconstruct_objects
from .huffman import DictionaryEncoder, build_codebook
from .equivalence import EquivalencePartitioner, apply_equivalence, get_equivalence_classes

__all__ = [
    # Tokenizer
    'count_tokens',
    'get_token_stats',
    'is_tiktoken_available',
    # Schema extraction
    'extract_schema',
    'find_array_data',
    'reconstruct_objects',
    # Dictionary encoding
    'DictionaryEncoder',
    'build_codebook',
    # Equivalence partitioning
    'EquivalencePartitioner',
    'apply_equivalence',
    'get_equivalence_classes',
]
