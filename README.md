# distill-json

> **Get structured JSON from LLMs with 84% fewer tokens.**

[![PyPI version](https://img.shields.io/pypi/v/distill-json.svg?color=8B5CF6)](https://pypi.org/project/distill-json/)
[![Downloads](https://static.pepy.tech/badge/distill-json)](https://pepy.tech/project/distill-json)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/karthyick/DISTILL?style=social)](https://github.com/karthyick/DISTILL)

Every token sent to an LLM costs money. `distill-json` compresses your JSON payloads **60-85%** while staying LLM-readable — no binary blobs, no weird encodings, **100% lossless roundtrip**.

---

## The Problem

```
Before: 4.2 MB JSON → 50,000 tokens → $0.15 per Claude call
After:  611 KB JSON →  8,000 tokens → $0.024 per Claude call
                                    ↳ 84% cheaper, same analysis
```

At 10K calls/month, that's **$1,260 saved**. At 1M calls, **$126,000**.

⭐ **[Star on GitHub](https://github.com/karthyick/DISTILL)** if this saves you tokens.

---

## Benchmarks (Real Data)

| Dataset | Items | Original Tokens | Compressed | Reduction | Compression Ratio |
|---------|-------|-----------------|------------|-----------|-------------------|
| Large dataset | 10,000 | 100,001 | 15,092 | **84.9%** | **6.6×** |
| Events (3 fields) | 1,000 | 10,001 | 1,535 | **84.7%** | **6.5×** |
| Log entries | 500 | 5,801 | 1,372 | 76.3% | 4.2× |
| Simple repetitive | 100 | 701 | 180 | 74.3% | 3.9× |
| API responses | 200 | 2,201 | 817 | 62.9% | 2.7× |
| Partial repetition | 100 | — | — | 57.6% | ~2.4× |
| Mostly unique | 50 | — | — | 28.8% | ~1.4× |

**Best case**: arrays of structured objects with repeated field names or values (logs, events, DB rows, API responses).

---

## Install

```bash
pip install distill-json

# With accurate token counting (recommended)
pip install distill-json[tiktoken]
```

---

## Quick Start

```python
from distill import compress, decompress

data = [
    {"id": 1, "name": "Alice",   "role": "developer", "team": "backend",  "remote": True},
    {"id": 2, "name": "Bob",     "role": "developer", "team": "backend",  "remote": True},
    {"id": 3, "name": "Charlie", "role": "designer",  "team": "frontend", "remote": False},
    {"id": 4, "name": "Diana",   "role": "developer", "team": "backend",  "remote": True},
]

result = compress(data)
print(result["compressed"])
print(f"Reduced by {result['meta']['reduction_percent']}%")
# → Reduced by 72.5%

# 100% lossless — exact type preservation
original = decompress(result["compressed"])
assert original == data
```

Now pass `result["compressed"]` to your LLM instead of `json.dumps(data)` and pay 72.5% less.

---

## Why distill-json vs. alternatives

| Approach | Token Reduction | LLM-Readable | Lossless |
|----------|-----------------|--------------|----------|
| **distill-json** | **60-85%** | ✅ | ✅ |
| gzip / LZ77 | 70-90% | ❌ (binary) | ✅ |
| Manual field stripping | 10-30% | ✅ | ❌ |
| Summarization prompts | 50-80% | ✅ | ❌ (lossy) |
| Plain JSON | 0% | ✅ | ✅ |

---

## How It Works

3-layer compression pipeline:

```
Input JSON
    ↓
Layer 1: Schema Extraction (objects → tuples + field names)
    ↓
Layer 2: Dictionary Encoding (frequent values → single-letter codes a-z)
    ↓
Layer 3: Equivalence Partitioning (repeated tuples → #N references)
    ↓
Compressed JSON (still valid JSON, still LLM-readable)
```

**Layer contribution** on highly repetitive data:

| Layer | Contribution | Cumulative |
|-------|--------------|------------|
| Schema Extraction | ~70% | 70% |
| Dictionary Encoding | ~10% | 80% |
| Equivalence Partitioning | ~7% | 87% |

### Layer 1 — Schema Extraction
```
Input:  [{"name": "Alice", "role": "dev"}, {"name": "Bob", "role": "dev"}]
Output: schema=["name", "role"], tuples=[["Alice", "dev"], ["Bob", "dev"]]
```
Field names stored once, not per-object.

### Layer 2 — Dictionary Encoding
```
"developer" appears 100×  →  code "a"
"backend"   appears  80×  →  code "b"
```
Long repeated strings become single characters.

### Layer 3 — Equivalence Partitioning
```
Input:  ["abc", "abc", "abc", "abd"]
Output: equiv={"#0": "abc"}, data=["#0", "#0", "#0", "abd"]
```
Repeated records stored once with short references.

---

## Output Format

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

| Key | Purpose |
|-----|---------|
| `$.schema` | Field names in sorted order |
| `$.dict` | Value → single-letter code mapping |
| `$.equiv` | Tuple → reference mapping |
| `$._bare` | Original was bare list (not wrapped) |
| `data` | Compressed records (or original key name) |
| `_extra` | Preserved non-array data from original |

---

## API Reference

### `compress(data, level="auto")`

```python
result = compress(data)
# {
#     "compressed": "...",          # Compressed JSON string
#     "meta": {
#         "method": "schema+dict+equiv",
#         "original_tokens": 1520,
#         "compressed_tokens": 228,
#         "reduction_percent": 85.0,
#         "tokens_saved": 1292,
#         "schema_fields": 5,
#         "dict_codes": 12,
#         "equiv_classes": 3,
#     }
# }
```

### `decompress(compressed)`

100% lossless. Accepts either the string or the full result dict.

```python
original = decompress(result["compressed"])
original = decompress(result)
```

### `analyze(data)`

Estimate compression without actually compressing:

```python
from distill import analyze
analyze(data)
# {
#     "original_tokens": 1520, "compressible": True,
#     "schema_fields": 5, "total_tuples": 100,
#     "unique_values": 45, "repeated_tuples": 12,
#     "estimated_reduction": 75,
# }
```

### Utilities

```python
from distill import compress_to_string, is_distill_format
from distill.core.tokenizer import count_tokens

compressed = compress_to_string(data)      # Just the string, no metadata
if is_distill_format(text):                # Detect distilled payloads
    original = decompress(text)
tokens = count_tokens(json_string)
```

---

## Type Preservation

Strings and primitives stay distinct through roundtrip:

```python
{"value": "123"}   # stays string
{"value": 123}     # stays int
{"value": "null"}  # stays string
{"value": None}    # stays None
{"value": "true"}  # stays string
{"value": True}    # stays bool
```

---

## Configuration

```python
from distill.config import with_config

with with_config(
    max_depth=100,
    dict_min_frequency=2,
    min_equiv_count=2,
    fallback_on_increase=True,  # Return original if compression would grow size
):
    result = compress(data)
```

---

## Error Handling

```python
from distill.exceptions import (
    DistillError,        # Base
    CompressionError,
    DecompressionError,
    ValidationError,     # NaN, Inf, sets
    InvalidInputError,   # None or empty
)

try:
    result = compress(data)
except InvalidInputError as e:
    ...
except ValidationError as e:
    ...
```

---

## Requirements

- Python 3.9+
- Optional: `tiktoken` for accurate token counting

---

## Ecosystem — other tools by the same author

If `distill-json` saves you tokens, these might save you more:

| Package | What it does |
|---------|--------------|
| [**semantic-llm-cache**](https://pypi.org/project/semantic-llm-cache/) | Cache LLM responses by semantic similarity — skip duplicate calls entirely |
| [**tracemaid**](https://pypi.org/project/tracemaid/) | Visualize execution traces of your Python + LLM workflows |
| [**langgraph-crosschain**](https://pypi.org/project/langgraph-crosschain/) | Cross-chain node communication for multi-agent LangGraph systems |

---

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Issues and PRs welcome. Before opening a PR, please run the test suite.

---

## ⭐ Star on GitHub

If this saved you tokens or cost, [star the repo](https://github.com/karthyick/DISTILL) — it helps others find it.

Built by [Karthick Raja M](https://github.com/karthyick) · [aichargeworks.com](https://aichargeworks.com)
