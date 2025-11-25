"""
Token counting utility for DISTILL.

Uses tiktoken (cl100k_base) for accurate OpenAI-compatible token counting.
Falls back to word-based approximation if tiktoken is not available.
"""

from typing import Union

# Try to import tiktoken, fall back to approximation
_tiktoken_available = False
_encoder = None

try:
    import tiktoken
    _encoder = tiktoken.get_encoding("cl100k_base")
    _tiktoken_available = True
except ImportError:
    pass


def count_tokens(text: Union[str, dict, list]) -> int:
    """
    Count the number of tokens in the given text or data structure.

    Args:
        text: String, dict, or list to count tokens for.
              If dict/list, converts to string first.

    Returns:
        Number of tokens (int)

    Examples:
        >>> count_tokens("Hello world")
        2
        >>> count_tokens({"key": "value"})
        5
    """
    if isinstance(text, (dict, list)):
        import json
        text = json.dumps(text, separators=(',', ':'))

    if not isinstance(text, str):
        text = str(text)

    if _tiktoken_available and _encoder is not None:
        return len(_encoder.encode(text))
    else:
        # Fallback: approximate token count
        # Average English word ≈ 1.3 tokens
        # Account for punctuation and special chars
        words = text.split()
        punctuation_count = sum(1 for c in text if c in '{}[]():,."\'')
        return int(len(words) * 1.3 + punctuation_count * 0.5)


def is_tiktoken_available() -> bool:
    """Check if tiktoken is available for accurate counting."""
    return _tiktoken_available


def get_token_stats(original: str, compressed: str) -> dict:
    """
    Calculate token statistics for compression comparison.

    Args:
        original: Original text/JSON string
        compressed: Compressed output string

    Returns:
        Dictionary with token statistics
    """
    original_tokens = count_tokens(original)
    compressed_tokens = count_tokens(compressed)

    reduction = 0.0
    if original_tokens > 0:
        reduction = ((original_tokens - compressed_tokens) / original_tokens) * 100

    return {
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "reduction_percent": round(reduction, 1),
        "tokens_saved": original_tokens - compressed_tokens
    }
