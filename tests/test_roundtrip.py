"""
Comprehensive roundtrip tests for DISTILL.

These tests verify 100% lossless roundtrip for all JSON data types and edge cases.
This is the MOST CRITICAL test file - compression is worthless if it's not lossless.
"""

import pytest
import json
import math

from distill import compress, decompress


def assert_roundtrip(data, msg=""):
    """Assert that data survives compress/decompress roundtrip exactly."""
    result = compress(data)

    # Handle fallback case (compression returned original)
    if result["meta"].get("fallback"):
        restored = json.loads(result["compressed"])
    else:
        restored = decompress(result["compressed"])

    # Deep equality check
    assert restored == data, f"Roundtrip failed{': ' + msg if msg else ''}\nOriginal: {data}\nRestored: {restored}"
    return result


class TestRoundtripBasic:
    """Basic roundtrip tests."""

    def test_simple_array(self):
        """Basic array of objects."""
        data = {"events": [{"a": 1}, {"a": 2}]}
        assert_roundtrip(data)

    def test_wrapped_array(self):
        """Array wrapped in dict key."""
        data = {"items": [{"x": "hello"}, {"x": "world"}]}
        assert_roundtrip(data)

    def test_with_extra_data(self):
        """Dict with array + other keys."""
        data = {
            "events": [{"type": "click"}, {"type": "view"}],
            "meta": {"count": 2, "version": "1.0"}
        }
        assert_roundtrip(data)

    def test_bare_list(self):
        """List without wrapper dict."""
        data = [{"a": 1}, {"a": 2}, {"a": 3}]
        assert_roundtrip(data)


class TestRoundtripTypes:
    """Roundtrip tests for all JSON types."""

    def test_string_values(self):
        """String values preserved."""
        data = {"items": [{"s": "hello"}, {"s": "world"}]}
        assert_roundtrip(data)

    def test_integer_values(self):
        """Integer values preserved (not converted to float)."""
        data = {"items": [{"i": 0}, {"i": 42}, {"i": -100}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        # Verify they're still integers
        for item in restored["items"]:
            assert isinstance(item["i"], int), f"Expected int, got {type(item['i'])}"

    def test_float_values(self):
        """Float values preserved with precision."""
        data = {"items": [{"f": 3.14}, {"f": 2.718}, {"f": 0.001}]}
        assert_roundtrip(data)

    def test_float_precision(self):
        """Float precision preserved."""
        data = {"items": [{"f": 1.23456789012345}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        assert restored["items"][0]["f"] == 1.23456789012345

    def test_large_integers(self):
        """Large integers preserved."""
        data = {"items": [{"n": 10**15}, {"n": -10**15}]}
        assert_roundtrip(data)

    def test_boolean_true(self):
        """Boolean True preserved (not string)."""
        data = {"items": [{"b": True}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        assert restored["items"][0]["b"] is True
        assert type(restored["items"][0]["b"]) is bool

    def test_boolean_false(self):
        """Boolean False preserved (not string)."""
        data = {"items": [{"b": False}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        assert restored["items"][0]["b"] is False
        assert type(restored["items"][0]["b"]) is bool

    def test_null_values(self):
        """Null/None values preserved."""
        data = {"items": [{"n": None}, {"n": None}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        assert restored["items"][0]["n"] is None

    def test_mixed_types(self):
        """Mixed types in same array."""
        data = {
            "items": [
                {"string": "hello", "int": 42, "float": 3.14, "bool": True, "null": None}
            ]
        }
        assert_roundtrip(data)


class TestRoundtripStrings:
    """Roundtrip tests for string edge cases."""

    def test_empty_string(self):
        """Empty string preserved."""
        data = {"items": [{"s": ""}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        assert restored["items"][0]["s"] == ""

    def test_string_null(self):
        """String 'null' preserved as string, not None."""
        data = {"items": [{"s": "null"}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        assert restored["items"][0]["s"] == "null"
        assert isinstance(restored["items"][0]["s"], str)

    def test_string_true(self):
        """String 'true' preserved as string, not boolean."""
        data = {"items": [{"s": "true"}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        assert restored["items"][0]["s"] == "true"
        assert isinstance(restored["items"][0]["s"], str)

    def test_string_false(self):
        """String 'false' preserved as string, not boolean."""
        data = {"items": [{"s": "false"}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        assert restored["items"][0]["s"] == "false"
        assert isinstance(restored["items"][0]["s"], str)

    def test_string_numeric(self):
        """String '123' preserved as string, not number."""
        data = {"items": [{"s": "123"}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        # Note: Due to type ambiguity, this may convert to int
        # This is a known limitation documented in huffman.py
        # For truly lossless string vs number, caller should use different field names

    def test_unicode_basic(self):
        """Basic unicode preserved."""
        data = {"items": [{"text": "日本語"}]}
        assert_roundtrip(data)

    def test_unicode_emoji(self):
        """Emoji preserved."""
        data = {"items": [{"text": "Hello 🌍 World 🎉"}]}
        assert_roundtrip(data)

    def test_unicode_mixed(self):
        """Mixed unicode scripts."""
        data = {"items": [{"text": "English 日本語 العربية"}]}
        assert_roundtrip(data)

    def test_newlines(self):
        """Newline characters preserved."""
        data = {"items": [{"text": "line1\nline2\nline3"}]}
        assert_roundtrip(data)

    def test_tabs(self):
        """Tab characters preserved."""
        data = {"items": [{"text": "col1\tcol2\tcol3"}]}
        assert_roundtrip(data)

    def test_special_chars(self):
        """Special characters preserved."""
        data = {"items": [{"text": r'quotes: "hello" and \'world\''}]}
        assert_roundtrip(data)

    def test_very_long_string(self):
        """Very long strings preserved."""
        long_text = "x" * 10000
        data = {"items": [{"text": long_text}]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        assert len(restored["items"][0]["text"]) == 10000


class TestRoundtripNested:
    """Roundtrip tests for nested structures."""

    def test_nested_dict(self):
        """Nested dict values preserved."""
        data = {"items": [{"nested": {"a": 1, "b": 2}}]}
        assert_roundtrip(data)

    def test_nested_array(self):
        """Nested array values preserved."""
        data = {"items": [{"arr": [1, 2, 3]}]}
        assert_roundtrip(data)

    def test_deeply_nested(self):
        """Deep nesting preserved."""
        data = {"items": [{"a": {"b": {"c": {"d": {"e": 1}}}}}]}
        assert_roundtrip(data)

    def test_mixed_nested(self):
        """Mixed nested structures."""
        data = {
            "items": [
                {
                    "obj": {"key": "value"},
                    "arr": [1, 2, 3],
                    "mixed": {"list": [{"nested": True}]}
                }
            ]
        }
        assert_roundtrip(data)


class TestRoundtripEquivalence:
    """Tests for equivalence partitioning roundtrip."""

    def test_repeated_items(self):
        """Repeated items use equivalence but still roundtrip."""
        data = {
            "events": [
                {"type": "click", "page": "home"},
                {"type": "click", "page": "home"},
                {"type": "click", "page": "home"},
            ]
        }
        result = assert_roundtrip(data)
        # Verify equivalence was used
        if not result["meta"].get("fallback"):
            compressed = json.loads(result["compressed"])
            assert "equiv" in compressed.get("$", {}) or result["meta"]["method"] == "schema+dict+equiv"

    def test_no_repetition(self):
        """Unique items still roundtrip."""
        data = {
            "events": [
                {"type": "a", "page": "1"},
                {"type": "b", "page": "2"},
                {"type": "c", "page": "3"},
            ]
        }
        assert_roundtrip(data)

    def test_partial_repetition(self):
        """Mix of repeated and unique items."""
        data = {
            "events": [
                {"type": "click", "page": "home"},  # repeated
                {"type": "view", "page": "about"},  # unique
                {"type": "click", "page": "home"},  # repeated
            ]
        }
        assert_roundtrip(data)


class TestRoundtripEdgeCases:
    """Edge case roundtrip tests."""

    def test_empty_array(self):
        """Empty array roundtrip."""
        data = {"items": []}
        assert_roundtrip(data)

    def test_empty_dict(self):
        """Empty dict roundtrip."""
        data = {}
        assert_roundtrip(data)

    def test_single_item(self):
        """Single item array."""
        data = {"items": [{"x": 1}]}
        assert_roundtrip(data)

    def test_single_field(self):
        """Objects with single field."""
        data = {"items": [{"x": 1}, {"x": 2}]}
        assert_roundtrip(data)

    def test_many_fields(self):
        """Objects with many fields."""
        obj = {f"field_{i}": i for i in range(50)}
        data = {"items": [obj, obj.copy()]}
        assert_roundtrip(data)

    def test_inconsistent_keys(self):
        """Objects with different keys."""
        data = {
            "items": [
                {"a": 1, "b": 2},
                {"a": 3, "c": 4},  # different keys
                {"b": 5, "c": 6},
            ]
        }
        assert_roundtrip(data)

    def test_values_like_codes(self):
        """String values that look like dictionary codes."""
        data = {"items": [{"x": "a"}, {"x": "b"}, {"x": "c"}]}
        assert_roundtrip(data)

    def test_values_like_refs(self):
        """String values that look like equivalence refs."""
        data = {"items": [{"x": "#0"}, {"x": "#1"}, {"x": "#2"}]}
        assert_roundtrip(data)

    def test_special_field_names(self):
        """Field names with special characters."""
        data = {"items": [{"field-name": 1, "field.name": 2, "field name": 3}]}
        assert_roundtrip(data)

    def test_large_array(self):
        """Large array roundtrip."""
        data = {"items": [{"i": i, "s": f"value_{i}"} for i in range(100)]}
        result = assert_roundtrip(data)
        # Verify order preserved
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        for i, item in enumerate(restored["items"]):
            assert item["i"] == i


class TestRoundtripParametrized:
    """Parametrized roundtrip tests."""

    @pytest.mark.parametrize("data", [
        {"a": [{"x": 1}]},
        {"a": [{"x": 1}, {"x": 1}]},
        [{"x": 1}],
        {"a": [{"x": None}]},
        {"a": [{"x": True}]},
        {"a": [{"x": False}]},
        {"a": [{"x": ""}]},
        {"a": [{"x": 0}]},
        {"a": [{"x": 0.0}]},
        {"a": [{"x": -1}]},
        {"a": [{"x": []}]},
        {"a": [{"x": {}}]},
    ])
    def test_parametrized_roundtrip(self, data):
        """Parametrized roundtrip for various data patterns."""
        assert_roundtrip(data)


class TestRoundtripPreservesOrder:
    """Tests that verify order preservation."""

    def test_array_order_preserved(self):
        """Array item order preserved."""
        data = {"items": [{"i": i} for i in range(20)]}
        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])
        for i, item in enumerate(restored["items"]):
            assert item["i"] == i, f"Order not preserved at index {i}"

    def test_field_values_match_original(self):
        """Field values exactly match original."""
        import random
        random.seed(42)  # Deterministic

        values = [random.randint(0, 1000) for _ in range(50)]
        data = {"items": [{"v": v} for v in values]}

        result = assert_roundtrip(data)
        restored = decompress(result) if not result["meta"].get("fallback") else json.loads(result["compressed"])

        restored_values = [item["v"] for item in restored["items"]]
        assert restored_values == values
