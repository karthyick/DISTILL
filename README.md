# DISTILL

**Data Intelligent Structure Token-efficient Interchange for LLMs**

A Python package that compresses JSON data for LLM consumption while maintaining semantic readability. Unlike binary compression (gzip, LZ77), DISTILL preserves meaning while reducing token count by **60-85%**.

## Why DISTILL?

When sending data to LLMs, every token counts:
- **Cost**: Less tokens = lower API costs
- **Context**: Fit more data in the context window
- **Speed**: Fewer tokens = faster responses

DISTILL compresses JSON while keeping it **LLM-readable** - no binary blobs, no unreadable encodings.

> **Best For**: DISTILL achieves maximum compression (60-85%) on **repetitive, structured data** - arrays of objects with repeated field names and values (logs, events, API responses, database records). For mostly unique data with no repetition, compression benefits are minimal (~20-30%).

## Installation

```bash
pip install distill-json

# With accurate token counting (recommended)
pip install distill-json[tiktoken]
```

## Quick Start

```python
from distill import compress, decompress

# Your JSON data
data = [
    {"id": 1, "name": "Alice", "role": "developer", "team": "backend", "remote": True},
    {"id": 2, "name": "Bob", "role": "developer", "team": "backend", "remote": True},
    {"id": 3, "name": "Charlie", "role": "designer", "team": "frontend", "remote": False},
    {"id": 4, "name": "Diana", "role": "developer", "team": "backend", "remote": True},
]

# Compress
result = compress(data)

print(result["compressed"])
print(f"Reduced by {result['meta']['reduction_percent']}%")
# Output: Reduced by 72.5%

# Decompress back to original (100% lossless)
original = decompress(result["compressed"])
assert original == data  # Exact match guaranteed
```

## How It Works

DISTILL uses a **3-layer compression architecture**:

```
Input JSON
    ↓
Layer 1: Schema Extraction (objects → tuples + field names)
    ↓
Layer 2: Dictionary Encoding (frequent values → single-letter codes a-z)
    ↓
Layer 3: Equivalence Partitioning (repeated tuples → #N references)
    ↓
Output: Compressed JSON
```

### Layer 1: Schema Extraction

Extracts field names into a schema, converts objects to value tuples:

```
Input:  [{"name": "Alice", "role": "dev"}, {"name": "Bob", "role": "dev"}]
Output: schema=["name", "role"], tuples=[["Alice", "dev"], ["Bob", "dev"]]
```

**Benefit**: Field names stored once instead of repeated per object.

### Layer 2: Dictionary Encoding

Maps frequent values to single-letter codes (a-z, max 26):

```
Frequency analysis: "dev" appears 100x, "home" appears 80x
Dictionary: {"a": "dev", "b": "home", ...}
Encoded: "dev" → "a", "home" → "b"
```

**Benefit**: Long repeated strings become single characters.

### Layer 3: Equivalence Partitioning

Groups identical encoded tuples into references:

```
Input:  ["abc", "abc", "abc", "abd"]
Output: equiv={"#0": "abc"}, data=["#0", "#0", "#0", "abd"]
```

**Benefit**: Repeated records stored once with short references.

## Output Format

DISTILL produces a JSON structure with a `$` metadata section:

```json
{
  "$": {
    "schema": ["name", "role", "team"],
    "dict": {"a": "\"developer\"", "b": "\"backend\"", "c": "\"frontend\""},
    "equiv": {"#0": "abc"}
  },
  "data": ["#0", "#0", "acd", "#0"]
}
```

### Format Breakdown

| Key | Purpose | Example |
|-----|---------|---------|
| `$.schema` | Field names in sorted order | `["name", "role", "team"]` |
| `$.dict` | Value → code mapping | `{"a": "\"click\"", "b": "\"home\""}` |
| `$.equiv` | Tuple → reference mapping | `{"#0": "abc", "#1": "abd"}` |
| `$.\_bare` | Original was bare list (not wrapped) | `true` |
| `data` | Compressed records (or original key name) | `["#0", "#0", "abc"]` |
| `_extra` | Preserved non-array data from original | `{"meta": {"count": 100}}` |

## API Reference

### compress(data, level="auto")

Compress JSON data for LLM consumption.

**Parameters:**
- `data`: JSON-compatible data (dict, list, or JSON string)
- `level`: Compression level (kept for API compatibility, uses optimal settings)

**Returns:**
```python
{
    "compressed": "...",  # Compressed JSON string
    "meta": {
        "method": "schema+dict+equiv",
        "original_tokens": 1520,
        "compressed_tokens": 228,
        "reduction_percent": 85.0,
        "tokens_saved": 1292,
        "schema_fields": 5,
        "dict_codes": 12,
        "equiv_classes": 3,
        "data_key": "events",
        "has_extra": False
    }
}
```

### decompress(compressed)

Reconstruct original JSON from compressed output. **100% lossless guaranteed.**

**Parameters:**
- `compressed`: DISTILL compressed string or result dict from `compress()`

**Returns:**
- Original JSON-compatible data structure (exact match)

```python
# Both work:
original = decompress(result["compressed"])
original = decompress(result)  # Pass whole result dict
```

### analyze(data)

Analyze data for compression potential without compressing.

```python
from distill import analyze

analysis = analyze(data)
print(analysis)
# {
#     "original_tokens": 1520,
#     "compressible": True,
#     "schema_fields": 5,
#     "total_tuples": 100,
#     "unique_values": 45,
#     "repeated_tuples": 12,
#     "estimated_reduction": 75,
#     "data_key": "events"
# }
```

### Utility Functions

```python
from distill import compress_to_string, is_distill_format
from distill.core.tokenizer import count_tokens

# Get just the compressed string (no metadata)
compressed = compress_to_string(data)

# Check if text is DISTILL format
if is_distill_format(text):
    original = decompress(text)

# Count tokens
tokens = count_tokens(json_string)
```

## Performance Metrics

| Dataset | Items | Original | Compressed | Reduction | Ratio |
|---------|-------|----------|------------|-----------|-------|
| Simple repetitive | 100 | 701 | 180 | 74.3% | **3.9x** |
| Events (3 fields) | 1,000 | 10,001 | 1,535 | 84.7% | **6.5x** |
| Large dataset | 10,000 | 100,001 | 15,092 | 84.9% | **6.6x** |
| Log entries | 500 | 5,801 | 1,372 | 76.3% | **4.2x** |
| API responses | 200 | 2,201 | 817 | 62.9% | **2.7x** |
| Partial repetition | 100 | - | - | 57.6% | ~2.4x |
| Mostly unique | 50 | - | - | 28.8% | ~1.4x |

### Compression Factor Analysis

For highly repetitive data (100 identical records):

| Layer | Contribution | Cumulative |
|-------|--------------|------------|
| Schema Extraction | ~70% | 70% |
| Dictionary Encoding | ~10% | 80% |
| Equivalence Partitioning | ~7% | 87% |

## Type Preservation

DISTILL guarantees **100% lossless roundtrip** with exact type preservation:

```python
# These remain distinct after compression/decompression:
{"value": "123"}   # String "123"
{"value": 123}     # Integer 123
{"value": "null"}  # String "null"
{"value": None}    # Actual null
{"value": "true"}  # String "true"
{"value": True}    # Boolean true
```

## Configuration

```python
from distill.config import with_config

# Customize compression settings
with with_config(
    max_depth=100,           # Max nesting depth (default: 50)
    dict_min_frequency=2,    # Min occurrences for dictionary (default: 1)
    min_equiv_count=2,       # Min occurrences for equivalence (default: 2)
    fallback_on_increase=True  # Return original if compression increases size
):
    result = compress(data)
```

## Error Handling

```python
from distill.exceptions import (
    DistillError,           # Base exception
    CompressionError,       # Compression failed
    DecompressionError,     # Decompression failed
    ValidationError,        # Invalid data (NaN, Inf, sets)
    InvalidInputError       # None or empty input
)

try:
    result = compress(data)
except InvalidInputError as e:
    print(f"Bad input: {e}")
except ValidationError as e:
    print(f"Invalid data: {e}")
except CompressionError as e:
    print(f"Compression failed: {e}")
```

## Requirements

- Python 3.9+
- Optional: `tiktoken` for accurate token counting

## License

MIT License

## Contributing

Contributions welcome! Please read our contributing guidelines.
