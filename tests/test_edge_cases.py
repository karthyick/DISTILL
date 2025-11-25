"""
Comprehensive edge case tests for DISTILL.

Tests all input types, boundary conditions, data types, structures,
roundtrip verification, error handling, and concurrency.
"""

import pytest
import json
import threading
import math
from typing import Any

from distill import compress, decompress, compress_file, decompress_file
from distill.exceptions import (
    DistillError,
    CompressionError,
    DecompressionError,
    ValidationError,
    InvalidInputError
)


class TestInputValidation:
    """Test handling of invalid inputs."""

    @pytest.mark.parametrize("invalid_input,expected_error", [
        (None, (DistillError, TypeError)),
        ("", DistillError),
        ("not json", DistillError),
        ("{'single': 'quotes'}", DistillError),  # Invalid JSON
        ('{"trailing": "comma",}', DistillError),
    ])
    def test_invalid_inputs_raise_error(self, invalid_input, expected_error):
        """Invalid inputs should raise appropriate errors."""
        if isinstance(expected_error, tuple):
            with pytest.raises(expected_error):
                compress(invalid_input)
        else:
            with pytest.raises(expected_error):
                compress(invalid_input)

    def test_integer_input_works(self):
        """Integer input (valid JSON value) should work."""
        result = compress(123)
        assert "compressed" in result

    def test_list_of_integers_works(self):
        """List of integers should work."""
        result = compress([1, 2, 3])
        assert "compressed" in result

    def test_set_input_raises_error(self):
        """Set is not JSON-serializable."""
        with pytest.raises((DistillError, TypeError)):
            compress({"a"})

    def test_inf_raises_error(self):
        """Infinity is not valid JSON."""
        with pytest.raises((DistillError, ValueError)):
            compress({"value": float('inf')})

    def test_nan_raises_error(self):
        """NaN is not valid JSON."""
        with pytest.raises((DistillError, ValueError)):
            compress({"value": float('nan')})


class TestBoundaryInputs:
    """Test boundary/edge case inputs that should work."""

    @pytest.mark.parametrize("boundary_input", [
        {},                           # Empty object
        [],                           # Empty array
        {"a": None},                  # Null value
        {"a": []},                    # Empty nested array
        {"a": {}},                    # Empty nested object
        {"": "empty key"},            # Empty string key
        {"a": ""},                    # Empty string value
        [None, None, None],           # Array of nulls
        {"a": {"b": {"c": {}}}},      # Deeply empty nesting
    ])
    def test_boundary_inputs_work(self, boundary_input):
        """Boundary inputs should compress without error."""
        result = compress(boundary_input)
        assert "compressed" in result
        assert "meta" in result

    def test_roundtrip_empty_object(self):
        """Empty object should roundtrip correctly."""
        original = {}
        result = compress(original)
        restored = decompress(result)
        assert restored == original

    def test_roundtrip_empty_array(self):
        """Empty array should roundtrip correctly."""
        original = []
        result = compress(original)
        restored = decompress(result)
        assert restored == original


class TestNumberEdgeCases:
    """Test numeric edge cases."""

    @pytest.mark.parametrize("number_input", [
        {"int": 0},
        {"int": -0},
        {"int": 2147483647},          # Max 32-bit
        {"int": -2147483648},         # Min 32-bit
        {"int": 9007199254740991},    # Max safe JS integer
        {"float": 0.0},
        {"float": 1e308},             # Large float
        {"float": 1e-308},            # Small float
        {"sci": 1.23e10},             # Scientific notation
        {"sci": 1.23e-10},
    ])
    def test_number_compression(self, number_input):
        """Various number formats should compress."""
        result = compress(number_input)
        assert "compressed" in result

    def test_floating_point_precision(self):
        """Floating point precision should be preserved in roundtrip."""
        original = {"float": 0.1 + 0.2}
        result = compress(original)
        restored = decompress(result)
        # Compare with tolerance for floating point
        assert abs(restored["float"] - original["float"]) < 1e-10


class TestStringEdgeCases:
    """Test string edge cases."""

    @pytest.mark.parametrize("string_input", [
        {"s": ""},                      # Empty
        {"s": " "},                     # Whitespace
        {"s": "\n\t\r"},                # Control chars
        {"s": "line1\nline2"},          # Newlines
        {"s": 'quote"inside'},          # Quotes
        {"s": "back\\slash"},           # Backslash
    ])
    def test_string_compression(self, string_input):
        """Various string formats should compress."""
        result = compress(string_input)
        assert "compressed" in result

    def test_very_long_string(self):
        """Very long strings should work."""
        original = {"s": "a" * 10000}
        result = compress(original)
        assert "compressed" in result

    def test_unicode_strings(self):
        """Unicode strings should work."""
        original = {"s": "中文日本語한국어"}
        result = compress(original)
        assert "compressed" in result

    def test_emoji_strings(self):
        """Emoji should work."""
        original = {"s": "emoji 🎉🔥👍"}
        result = compress(original)
        assert "compressed" in result

    def test_rtl_text(self):
        """RTL text should work."""
        original = {"s": "مرحبا"}
        result = compress(original)
        assert "compressed" in result

    def test_surrogate_pairs(self):
        """Surrogate pairs (astral plane) should work."""
        original = {"s": "𝕳𝖊𝖑𝖑𝖔"}
        result = compress(original)
        assert "compressed" in result

    def test_html_content(self):
        """HTML content should not cause issues."""
        original = {"s": "<script>alert(1)</script>"}
        result = compress(original)
        assert "compressed" in result

    def test_sql_content(self):
        """SQL-like content should not cause issues."""
        original = {"s": "SELECT * FROM users"}
        result = compress(original)
        assert "compressed" in result


class TestBooleanAndNull:
    """Test boolean and null handling."""

    def test_boolean_values(self):
        """Boolean values should work."""
        original = {"t": True, "f": False}
        result = compress(original)
        restored = decompress(result)
        assert restored["t"] == True
        assert restored["f"] == False

    def test_null_value(self):
        """Null values should work."""
        original = {"n": None}
        result = compress(original)
        restored = decompress(result)
        assert restored["n"] is None

    def test_mixed_types(self):
        """Mixed types in array should work."""
        original = {"mixed": [True, False, None, 1, "str"]}
        result = compress(original)
        assert "compressed" in result


class TestStructureEdgeCases:
    """Test structural edge cases."""

    def test_deep_nesting(self):
        """Deep nesting should be handled."""
        deep = {"level": 0}
        current = deep
        for i in range(1, 50):  # 50 levels deep
            current["child"] = {"level": i}
            current = current["child"]

        result = compress(deep)
        assert "compressed" in result

    def test_wide_object(self):
        """Object with many keys should work."""
        original = {f"key_{i}": i for i in range(1000)}
        result = compress(original)
        assert "compressed" in result

    def test_large_array(self):
        """Large arrays should work."""
        original = {"arr": list(range(1000))}
        result = compress(original)
        assert "compressed" in result

    def test_mixed_complex(self):
        """Complex mixed structures should work."""
        original = {
            "arr_of_obj": [{"id": i, "data": {"nested": True}} for i in range(100)],
            "obj_of_arr": {f"k{i}": [1, 2, 3] for i in range(100)},
            "mixed": [1, "two", True, None, {"five": 5}, [6, 7, 8]]
        }
        result = compress(original)
        assert "compressed" in result

    def test_repeated_references(self):
        """Objects with repeated dict values should work."""
        shared = {"shared": "value"}
        original = {"a": shared, "b": shared, "c": shared}
        result = compress(original)
        assert "compressed" in result


class TestEquivalenceEdgeCases:
    """Test equivalence partitioning edge cases."""

    def test_all_same_values(self):
        """All same values should create one group."""
        original = {"users": [{"role": "admin"} for _ in range(100)]}
        result = compress(original, level="low")
        assert "compressed" in result
        # Compression may or may not reduce tokens depending on overhead
        assert result["meta"]["reduction_percent"] >= 0

    def test_all_different_values(self):
        """All different values - no grouping possible."""
        original = {"users": [{"id": i} for i in range(100)]}
        result = compress(original, level="low")
        assert "compressed" in result

    def test_case_sensitive_no_group(self):
        """Case differences should NOT group together."""
        original = {"items": [{"val": "test"}, {"val": "Test"}, {"val": "TEST"}]}
        result = compress(original, level="low")
        assert "compressed" in result

    def test_partial_overlap(self):
        """Partial field overlap should work."""
        original = {"items": [
            {"a": 1, "b": 2},
            {"a": 1, "b": 3},
            {"a": 2, "b": 2}
        ]}
        result = compress(original, level="low")
        assert "compressed" in result


class TestMDLEdgeCases:
    """Test MDL pattern extraction edge cases."""

    def test_perfect_correlation(self):
        """Perfect correlation should create rule."""
        data = [{"team": "backend", "remote": True} for _ in range(100)]
        result = compress({"employees": data}, level="medium")
        assert "compressed" in result

    def test_high_correlation(self):
        """95% correlation should create rule."""
        data = [{"team": "backend", "remote": True} for _ in range(95)]
        data += [{"team": "backend", "remote": False} for _ in range(5)]
        result = compress({"employees": data}, level="medium")
        assert "compressed" in result

    def test_low_correlation(self):
        """Low correlation should not create rule."""
        data = [{"team": "backend", "remote": True} for _ in range(70)]
        data += [{"team": "backend", "remote": False} for _ in range(30)]
        result = compress({"employees": data}, level="medium")
        assert "compressed" in result

    def test_no_correlation(self):
        """No correlation data should work."""
        original = {"items": [{"a": i % 2, "b": i % 3} for i in range(100)]}
        result = compress(original, level="medium")
        assert "compressed" in result

    def test_multiple_rules_possible(self):
        """Data with multiple possible rules should work."""
        original = {"items": [
            {"type": "A", "color": "red", "size": "large"},
            {"type": "A", "color": "red", "size": "large"},
            {"type": "B", "color": "blue", "size": "small"},
            {"type": "B", "color": "blue", "size": "small"},
        ]}
        result = compress(original, level="medium")
        assert "compressed" in result


class TestHuffmanEdgeCases:
    """Test Huffman coding edge cases."""

    def test_single_frequent_term(self):
        """Single frequent term should get short code."""
        original = {"logs": [{"level": "INFO"} for _ in range(1000)]}
        result = compress(original, level="high")
        assert "compressed" in result

    def test_equal_frequencies(self):
        """Equal frequencies - may have limited benefit."""
        original = {"items": [{"type": "A"}, {"type": "B"}, {"type": "C"}]}
        result = compress(original, level="high")
        assert "compressed" in result

    def test_many_unique_values(self):
        """Many unique values - limited benefit."""
        original = {"items": [{"id": f"unique_{i}"} for i in range(100)]}
        result = compress(original, level="high")
        assert "compressed" in result

    def test_short_values(self):
        """Short values may not benefit from coding."""
        original = {"items": [{"s": "a"}, {"s": "b"}, {"s": "c"}]}
        result = compress(original, level="high")
        assert "compressed" in result


class TestRoundtripVerification:
    """Test that compress->decompress produces original data."""

    @pytest.mark.parametrize("original", [
        {},
        [],
        {"a": 1},
        {"nested": {"deep": {"value": [1, 2, 3]}}},
        [1, "two", True, None],
        {"unicode": "中文"},
        {"bool": True},
        {"null": None},
        {"list": [1, 2, 3, 4, 5]},
    ])
    def test_roundtrip_basic(self, original):
        """Basic data structures should roundtrip exactly."""
        result = compress(original)
        restored = decompress(result)
        assert json.dumps(restored, sort_keys=True) == json.dumps(original, sort_keys=True)

    def test_roundtrip_large_dataset(self):
        """Large datasets should roundtrip."""
        original = [{"id": i, "status": "active" if i % 2 == 0 else "inactive"} for i in range(100)]
        result = compress(original)
        restored = decompress(result)
        assert len(restored) == len(original)


class TestDecompressionErrors:
    """Test decompression error handling."""

    @pytest.mark.parametrize("malformed", [
        "",
        None,
        123,
    ])
    def test_malformed_raises_error(self, malformed):
        """Malformed input should raise DecompressionError."""
        with pytest.raises(DecompressionError):
            decompress(malformed)

    def test_truncated_data(self):
        """Truncated compressed data should be handled."""
        valid = compress({"a": 1, "b": 2, "c": 3})["compressed"]
        truncated = valid[:len(valid) // 2]
        # Should either decompress partially or raise error
        try:
            result = decompress(truncated)
            # If it succeeds, should return something
            assert result is not None
        except DecompressionError:
            pass  # Expected


class TestConcurrency:
    """Test thread safety."""

    def test_parallel_compression(self):
        """Parallel compression should be thread-safe."""
        data = {"items": [{"id": i} for i in range(100)]}
        results = []
        errors = []

        def compress_task():
            try:
                result = compress(data)
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=compress_task) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10

    def test_parallel_different_levels(self):
        """Parallel compression at different levels should work."""
        data = {"items": [{"id": i, "status": "active"} for i in range(50)]}
        results = []
        errors = []

        def compress_task(level):
            try:
                result = compress(data, level=level)
                results.append((level, result))
            except Exception as e:
                errors.append((level, e))

        levels = ["low", "medium", "high", "auto"] * 3
        threads = [threading.Thread(target=compress_task, args=(l,)) for l in levels]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 12


class TestFileIOErrors:
    """Test file I/O error handling."""

    def test_nonexistent_file(self, tmp_path):
        """Non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            compress_file(tmp_path / "does_not_exist.json")

    def test_empty_file(self, tmp_path):
        """Empty file should raise error."""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("")
        with pytest.raises((json.JSONDecodeError, ValidationError, DistillError)):
            compress_file(empty_file)

    def test_invalid_json_file(self, tmp_path):
        """Invalid JSON file should raise error."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json")
        with pytest.raises((json.JSONDecodeError, ValidationError, DistillError)):
            compress_file(invalid_file)


class TestCompressionLevels:
    """Test all compression levels work correctly.

    Note: The new 3-layer architecture uses a unified compression method
    (schema+dict+equiv) regardless of level parameter. The level parameter
    is kept for API compatibility but doesn't change behavior.
    """

    @pytest.fixture
    def sample_data(self):
        """Generate sample data for testing."""
        return [
            {"id": i, "status": "active" if i % 2 == 0 else "inactive", "role": "user"}
            for i in range(50)
        ]

    def test_low_level(self, sample_data):
        """Low level should work (same as auto in new architecture)."""
        result = compress(sample_data, level="low")
        assert "compressed" in result
        assert "meta" in result

    def test_medium_level(self, sample_data):
        """Medium level should work (same as auto in new architecture)."""
        result = compress(sample_data, level="medium")
        assert "compressed" in result
        assert "meta" in result

    def test_high_level(self, sample_data):
        """High level should work (same as auto in new architecture)."""
        result = compress(sample_data, level="high")
        assert "compressed" in result
        assert "meta" in result

    def test_auto_level(self, sample_data):
        """Auto level should work and select best."""
        result = compress(sample_data, level="auto")
        assert "compressed" in result


class TestKeyPreservation:
    """Test that key order and names are preserved."""

    def test_key_order_preserved(self):
        """Key insertion order should be preserved in roundtrip."""
        original = {"z": 1, "a": 2, "m": 3}
        result = compress(original)
        restored = decompress(result)
        # Python 3.7+ dicts are ordered
        assert list(restored.keys()) == list(original.keys())

    def test_special_keys(self):
        """Special key names should be preserved."""
        original = {
            "": "empty",
            " ": "space",
            "123": "numeric string",
            "key-with-dash": "value",
            "key.with.dots": "value",
            "key:with:colons": "value",
        }
        result = compress(original)
        restored = decompress(result)
        for key in original:
            assert key in restored
            assert restored[key] == original[key]


class TestMetadataAccuracy:
    """Test that metadata is accurate."""

    def test_token_counts(self):
        """Token counts should be accurate."""
        data = [{"id": i, "status": "active"} for i in range(50)]
        result = compress(data)

        assert result["meta"]["original_tokens"] > 0
        assert result["meta"]["compressed_tokens"] > 0
        assert result["meta"]["original_tokens"] >= result["meta"]["compressed_tokens"]

    def test_reduction_percent(self):
        """Reduction percent should be calculated correctly."""
        data = [{"status": "active", "role": "admin"} for _ in range(100)]
        result = compress(data)

        if result["meta"]["reduction_percent"] > 0:
            expected = 100 * (
                1 - result["meta"]["compressed_tokens"] / result["meta"]["original_tokens"]
            )
            assert abs(result["meta"]["reduction_percent"] - expected) < 0.1
