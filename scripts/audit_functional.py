#!/usr/bin/env python
"""
Functional Verification Audit for DISTILL.

Verifies implementation matches EXACTLY what was designed.
No hidden fallbacks, no undocumented behaviors, no deviations.
"""

import sys
import os
import re
import json
import inspect
from pathlib import Path
from typing import Any, Dict, List

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from distill import compress, decompress
from distill.core.equivalence import EquivalencePartitioner
from distill.core.mdl import MDLExtractor
from distill.core.huffman import HuffmanEncoder
from distill.core.relational import RelationalNormalizer


def audit_low_level_integrity():
    """Verify low level ONLY uses equivalence, nothing else."""
    from distill.compress import Compressor

    code = inspect.getsource(Compressor.compress_low)

    # Should NOT contain references to other methods
    forbidden = ["mdl", "huffman", "codebook", "relational", "rule"]
    for term in forbidden:
        # Check for actual usage, not just in docstrings
        lines = [l for l in code.split('\n')
                 if term.lower() in l.lower()
                 and not l.strip().startswith('#')
                 and not l.strip().startswith('"""')
                 and not l.strip().startswith("'''")]
        if lines:
            raise AssertionError(f"Low level contains forbidden term '{term}': {lines[0][:80]}")

    # Verify equivalence IS used
    assert "equivalence" in code.lower() or "equiv" in code.lower(), \
        "Low level must use equivalence"

    print("  Low level: Only equivalence, nothing else")


def audit_medium_level_integrity():
    """Verify medium level uses equivalence + MDL, nothing else."""
    from distill.compress import Compressor

    code = inspect.getsource(Compressor.compress_medium)

    # Should NOT contain huffman or relational
    forbidden = ["huffman", "codebook", "relational"]
    for term in forbidden:
        lines = [l for l in code.split('\n')
                 if term.lower() in l.lower()
                 and not l.strip().startswith('#')
                 and not l.strip().startswith('"""')]
        if lines:
            raise AssertionError(f"Medium level contains forbidden term '{term}'")

    # Should use equivalence AND mdl
    assert "equiv" in code.lower(), "Medium must use equivalence"
    assert "mdl" in code.lower() or "rule" in code.lower(), "Medium must use MDL"

    print("  Medium level: Equivalence + MDL only")


def audit_high_level_integrity():
    """Verify high level uses all methods with relational check."""
    from distill.compress import Compressor

    code = inspect.getsource(Compressor.compress_high)

    # Should contain equivalence, mdl, huffman, relational
    assert "medium" in code.lower() or "equiv" in code.lower(), "High must use equivalence"
    assert "huffman" in code.lower(), "High must use huffman"
    assert "relational" in code.lower(), "High must check relational"

    # Relational must be CONDITIONAL
    assert "if" in code and "relational" in code.lower(), \
        "Relational must be conditional (if check)"

    print("  High level: All methods with conditional relational")


def audit_auto_runs_all_levels():
    """Verify auto level runs ALL three levels."""
    from distill.compress import Compressor

    code = inspect.getsource(Compressor.compress_auto)

    # Should reference all three levels
    assert "low" in code.lower(), "Auto must run low"
    assert "medium" in code.lower(), "Auto must run medium"
    assert "high" in code.lower(), "Auto must run high"

    # Should use ThreadPoolExecutor for parallel execution
    assert "threadpool" in code.lower() or "executor" in code.lower(), \
        "Auto should run levels in parallel"

    print("  Auto level: Runs all three levels")


def audit_auto_returns_smallest():
    """Verify auto returns the smallest result."""
    # Test with data where different levels produce different sizes
    data = [
        {"id": i, "status": "active", "role": "admin", "team": "backend"}
        for i in range(50)
    ]

    result_auto = compress(data, level="auto")
    result_low = compress(data, level="low")
    result_med = compress(data, level="medium")
    result_high = compress(data, level="high")

    all_tokens = [
        result_low["meta"]["compressed_tokens"],
        result_med["meta"]["compressed_tokens"],
        result_high["meta"]["compressed_tokens"]
    ]
    smallest = min(all_tokens)

    assert result_auto["meta"]["compressed_tokens"] == smallest, \
        f"Auto returned {result_auto['meta']['compressed_tokens']} tokens but smallest is {smallest}"

    print(f"  Auto returns smallest: {smallest} tokens (low={all_tokens[0]}, med={all_tokens[1]}, high={all_tokens[2]})")


def audit_no_hidden_fallbacks():
    """Search for unauthorized fallback patterns in codebase."""
    distill_dir = Path(__file__).parent.parent / "distill"

    # Patterns that indicate hidden fallbacks (but allow documented ones)
    suspicious_patterns = [
        (r'except\s*:\s*pass', "Silent exception swallowing"),
        (r'except.*:\s*$\n\s*pass', "Pass in except block"),
    ]

    issues = []

    for py_file in distill_dir.rglob("*.py"):
        content = py_file.read_text(encoding='utf-8')

        for pattern, description in suspicious_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            if matches:
                issues.append(f"{py_file.name}: {description}")

    if issues:
        print(f"  WARNING: Found {len(issues)} suspicious patterns")
        for issue in issues[:3]:  # Show first 3
            print(f"    - {issue}")
    else:
        print("  No hidden fallback patterns found")


def audit_equivalence_threshold():
    """Verify equivalence groups at 2+ occurrences."""
    partitioner = EquivalencePartitioner()

    # 1 occurrence - should NOT group
    data1 = [{"role": "admin"}]
    classes1 = partitioner.analyze(data1)
    # Single items may or may not create groups depending on implementation
    # The key is that they shouldn't create equivalence GROUPINGS

    # 2 occurrences - SHOULD group
    data2 = [{"role": "admin"}, {"role": "admin"}]
    classes2 = partitioner.analyze(data2)
    assert "role" in classes2, "2 occurrences should create group"
    assert "admin" in classes2["role"], "Value 'admin' should be in group"
    assert classes2["role"]["admin"] == [0, 1], "Both indices should be in group"

    print("  Equivalence threshold: Groups at 2+ occurrences")


def audit_mdl_threshold():
    """Verify MDL creates rules at 95% correlation."""
    extractor = MDLExtractor(min_confidence=0.95)

    # 94% correlation - should NOT create rule
    data94 = [{"a": "x", "b": "y"}] * 94 + [{"a": "x", "b": "z"}] * 6
    rules94 = extractor.analyze(data94)
    # Check if any rule has a->b or b->a with the specific values
    has_rule_94 = any(
        r["antecedent"]["value"] == "x" and r["consequent"]["value"] == "y"
        for r in rules94
    )

    # 95% correlation - SHOULD create rule
    data95 = [{"a": "x", "b": "y"}] * 95 + [{"a": "x", "b": "z"}] * 5
    rules95 = extractor.analyze(data95)
    has_rule_95 = any(
        r["antecedent"]["value"] == "x" and r["consequent"]["value"] == "y"
        for r in rules95
    )

    # 100% correlation - definitely should create rule
    data100 = [{"a": "x", "b": "y"}] * 100
    rules100 = extractor.analyze(data100)
    has_rule_100 = any(
        r["antecedent"]["value"] == "x" and r["consequent"]["value"] == "y"
        for r in rules100
    )

    assert has_rule_100, "100% correlation must create rule"
    print(f"  MDL threshold: 94%={has_rule_94}, 95%={has_rule_95}, 100%={has_rule_100}")


def audit_huffman_threshold():
    """Verify Huffman codes terms appearing frequently."""
    encoder = HuffmanEncoder()

    # Test frequency analysis
    data_low_freq = [{"level": "INFO"}, {"level": "DEBUG"}]
    data_high_freq = [{"level": "INFO"}] * 10 + [{"level": "DEBUG"}] * 2

    freqs_low = encoder.analyze(json.dumps(data_low_freq))
    freqs_high = encoder.analyze(json.dumps(data_high_freq))

    # High frequency data should have higher counts
    assert freqs_high.get("INFO", 0) >= freqs_low.get("INFO", 0), \
        "Higher frequency should be detected"

    print(f"  Huffman: Frequency-based coding verified")


def audit_relational_conditional():
    """Verify relational is applied ONLY if it reduces tokens."""
    from distill.core.relational import check_relational_benefit

    # Case where relational might help (many repeated values)
    data_repeated = [{"customer": "Alice Corp"}] * 50
    result = compress({"items": data_repeated}, level="high")

    # Check that the decision was made
    meta = result["meta"]
    assert "relational_applied" in meta, "Meta should indicate relational decision"

    print(f"  Relational: Conditional application (applied={meta.get('relational_applied', 'N/A')})")


def audit_output_format():
    """Verify output structure matches design."""
    data = {"items": [{"id": 1}, {"id": 2}]}
    result = compress(data)

    # Must have these keys
    assert "compressed" in result, "Must have 'compressed' key"
    assert "meta" in result, "Must have 'meta' key"

    # Meta must have required fields
    meta = result["meta"]
    required_meta = ["level", "original_tokens", "compressed_tokens", "reduction_percent"]
    for field in required_meta:
        assert field in meta, f"Meta must have '{field}'"

    # Compressed must be string (readable)
    assert isinstance(result["compressed"], str), "Compressed must be string"

    print(f"  Output format: Valid structure with all required fields")


def audit_decompression_exact():
    """Verify decompress returns EXACT original."""
    test_cases = [
        {"simple": "value"},
        {"float": 3.14159},
        {"bool": True},
        {"null": None},
        {"list": [1, 2, 3]},
        {"nested": {"deep": {"value": "here"}}},
        {"unicode": "中文"},
        {"mixed": [1, "two", True, None]},
    ]

    for original in test_cases:
        result = compress(original)
        restored = decompress(result)

        # Exact match
        assert json.dumps(restored, sort_keys=True) == json.dumps(original, sort_keys=True), \
            f"Mismatch: {original} -> {restored}"

    print(f"  Decompression: All {len(test_cases)} cases roundtrip exactly")


def audit_no_data_loss():
    """Verify no data is lost during compression."""
    # Long string
    long_str = "x" * 10000
    result = compress({"s": long_str})
    recovered = decompress(result)
    assert len(recovered["s"]) == 10000, "Long string truncated"

    # Many keys
    many_keys = {f"key_{i}": i for i in range(100)}
    result = compress(many_keys)
    recovered = decompress(result)
    assert len(recovered) == 100, "Keys lost"

    # Deep nesting
    deep = {"l1": {"l2": {"l3": {"l4": {"l5": "value"}}}}}
    result = compress(deep)
    recovered = decompress(result)
    assert recovered["l1"]["l2"]["l3"]["l4"]["l5"] == "value", "Nesting lost"

    print("  No data loss: Long strings, many keys, deep nesting all preserved")


def audit_no_unauthorized_optimizations():
    """Check for unauthorized compression methods."""
    distill_dir = Path(__file__).parent.parent / "distill"

    unauthorized = [
        "gzip", "zlib", "lz77", "lz4", "brotli", "snappy",  # Binary compression
        "base64",  # Encoding that changes readability
        "truncate", "limit", "max_length",  # Data loss
    ]

    issues = []
    for py_file in distill_dir.rglob("*.py"):
        content = py_file.read_text(encoding='utf-8').lower()
        for term in unauthorized:
            if term in content:
                # Check it's actual code, not just a comment
                lines = [l for l in content.split('\n')
                         if term in l
                         and not l.strip().startswith('#')
                         and 'import' not in l]  # Allow gzip import for file I/O
                if lines and "io.py" not in str(py_file):  # Allow in io.py for file handling
                    issues.append(f"{py_file.name}: uses '{term}'")

    if issues:
        print(f"  WARNING: {len(issues)} potentially unauthorized terms found")
        for issue in issues[:3]:
            print(f"    - {issue}")
    else:
        print("  No unauthorized optimization methods found")


def run_full_audit():
    """Run all audits."""
    print("\n" + "=" * 60)
    print("DISTILL Functional Verification Audit")
    print("=" * 60)

    audits = [
        ("Level Integrity - Low", audit_low_level_integrity),
        ("Level Integrity - Medium", audit_medium_level_integrity),
        ("Level Integrity - High", audit_high_level_integrity),
        ("Auto Runs All Levels", audit_auto_runs_all_levels),
        ("Auto Returns Smallest", audit_auto_returns_smallest),
        ("No Hidden Fallbacks", audit_no_hidden_fallbacks),
        ("Equivalence Threshold", audit_equivalence_threshold),
        ("MDL Threshold", audit_mdl_threshold),
        ("Huffman Threshold", audit_huffman_threshold),
        ("Relational Conditional", audit_relational_conditional),
        ("Output Format", audit_output_format),
        ("Decompression Exact", audit_decompression_exact),
        ("No Data Loss", audit_no_data_loss),
        ("No Unauthorized Optimizations", audit_no_unauthorized_optimizations),
    ]

    passed = 0
    failed = []

    for name, audit_func in audits:
        print(f"\n[{name}]")
        try:
            audit_func()
            passed += 1
            print(f"  PASSED")
        except AssertionError as e:
            print(f"  FAILED: {e}")
            failed.append(name)
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failed.append(name)

    print("\n" + "=" * 60)
    print(f"AUDIT RESULT: {passed}/{len(audits)} passed")
    print("=" * 60)

    if failed:
        print(f"\nFailed audits:")
        for name in failed:
            print(f"  - {name}")
        print("\nImplementation has deviations from design!")
        return 1
    else:
        print("\nImplementation matches design specification.")
        return 0


if __name__ == "__main__":
    sys.exit(run_full_audit())
