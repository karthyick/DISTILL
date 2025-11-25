"""
Utility functions for DISTILL.
"""

from typing import Any, Dict, Optional
import json


def validate_json(data: Any) -> bool:
    """
    Validate that data is JSON-compatible.

    Args:
        data: Data to validate

    Returns:
        True if valid JSON structure, False otherwise
    """
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError):
        return False


def parse_json(data: Any) -> Any:
    """
    Parse JSON string or return data as-is if already parsed.

    Args:
        data: JSON string or already-parsed data

    Returns:
        Parsed JSON data
    """
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON string")
    return data


def pretty_print(result: Dict[str, Any]) -> str:
    """
    Pretty print compression result.

    Args:
        result: Result from compress()

    Returns:
        Formatted string for display
    """
    meta = result.get("meta", {})

    lines = [
        "=" * 50,
        "DISTILL Compression Result",
        "=" * 50,
        f"Method: {meta.get('method', 'unknown')}",
        "",
        "Token Statistics:",
        f"  Original:   {meta.get('original_tokens', 0):,} tokens",
        f"  Compressed: {meta.get('compressed_tokens', 0):,} tokens",
        f"  Reduction:  {meta.get('reduction_percent', 0):.1f}%",
        "",
        "Compressed Output:",
        "-" * 50,
        result.get("compressed", ""),
        "-" * 50,
    ]

    return "\n".join(lines)


def estimate_cost_savings(
    original_tokens: int,
    compressed_tokens: int,
    input_cost_per_million: float = 3.0,
    calls_per_day: int = 1000
) -> Dict[str, float]:
    """
    Estimate cost savings from compression.

    Args:
        original_tokens: Original token count
        compressed_tokens: Compressed token count
        input_cost_per_million: Cost per million input tokens (default: $3.00 for Claude Sonnet)
        calls_per_day: Number of API calls per day

    Returns:
        Dictionary with cost estimates
    """
    tokens_saved = original_tokens - compressed_tokens

    daily_tokens_saved = tokens_saved * calls_per_day
    monthly_tokens_saved = daily_tokens_saved * 30

    daily_cost_saved = (daily_tokens_saved / 1_000_000) * input_cost_per_million
    monthly_cost_saved = daily_cost_saved * 30

    return {
        "tokens_saved_per_call": tokens_saved,
        "daily_tokens_saved": daily_tokens_saved,
        "monthly_tokens_saved": monthly_tokens_saved,
        "daily_cost_saved_usd": round(daily_cost_saved, 2),
        "monthly_cost_saved_usd": round(monthly_cost_saved, 2)
    }


def analyze_data(data: Any) -> Dict[str, Any]:
    """
    Analyze data structure for compression potential.

    Args:
        data: JSON-compatible data

    Returns:
        Analysis dictionary
    """
    analysis = {
        "type": type(data).__name__,
        "is_list": isinstance(data, list),
        "is_dict": isinstance(data, dict),
        "nested_depth": _get_depth(data),
        "total_items": _count_items(data),
        "unique_keys": set(),
        "repeated_values": {},
    }

    if isinstance(data, list):
        analysis["list_length"] = len(data)

        # Analyze for repeated values
        if data and isinstance(data[0], dict):
            analysis["unique_keys"] = set(data[0].keys())
            value_counts: Dict[str, Dict[Any, int]] = {}

            for item in data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if key not in value_counts:
                            value_counts[key] = {}
                        if isinstance(value, (str, int, float, bool)):
                            hash_val = str(value)
                            value_counts[key][hash_val] = value_counts[key].get(hash_val, 0) + 1

            # Find repeated values
            for key, counts in value_counts.items():
                repeated = {v: c for v, c in counts.items() if c > 1}
                if repeated:
                    analysis["repeated_values"][key] = len(repeated)

    return analysis


def _get_depth(data: Any, current: int = 0) -> int:
    """Get maximum nesting depth of data structure."""
    if isinstance(data, dict):
        if not data:
            return current + 1
        return max(_get_depth(v, current + 1) for v in data.values())
    elif isinstance(data, list):
        if not data:
            return current + 1
        return max(_get_depth(item, current + 1) for item in data)
    return current


def _count_items(data: Any) -> int:
    """Count total items in data structure."""
    if isinstance(data, dict):
        return sum(1 + _count_items(v) for v in data.values())
    elif isinstance(data, list):
        return sum(1 + _count_items(item) for item in data)
    return 1
