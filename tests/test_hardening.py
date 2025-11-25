"""
Specific hardening tests for DISTILL.

Targeting the edge cases addressed in the review:
1. Inconsistent keys (MISSING values).
2. Collision values (strings looking like booleans, nulls, codes, refs).
3. Structural preservation (bare lists, extra data).
"""

import pytest
import json
from distill import compress, decompress

class TestHardening:
    
    def test_inconsistent_keys(self):
        """Test list of dicts with different keys (schema evolution)."""
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2},  # Missing name
            {"name": "Bob"},  # Missing id
            {}  # Missing both
        ]
        result = compress(data)
        restored = decompress(result)
        
        # Verify roundtrip
        # Note: missing keys are omitted in restored dicts, matching original
        assert len(restored) == 4
        assert restored[0] == {"id": 1, "name": "Alice"}
        assert restored[1] == {"id": 2}
        assert restored[2] == {"name": "Bob"}
        assert restored[3] == {}

    def test_collision_values_keywords(self):
        """Test strings that collide with JSON keywords."""
        data = [
            {"val": True},      # Boolean True
            {"val": "true"},    # String "true"
            {"val": False},     # Boolean False
            {"val": "false"},   # String "false"
            {"val": None},      # Null
            {"val": "null"},    # String "null"
        ]
        result = compress(data)
        restored = decompress(result)
        
        assert restored[0]["val"] is True
        assert restored[1]["val"] == "true"
        assert restored[2]["val"] is False
        assert restored[3]["val"] == "false"
        assert restored[4]["val"] is None
        assert restored[5]["val"] == "null"

    def test_collision_values_codes(self):
        """Test strings that look like dictionary codes."""
        # "a", "b", "c" might be used as codes.
        # If we have them as values, they should be preserved.
        data = [{"val": c} for c in "abcdefghijklmnopqrstuvwxyz"]
        result = compress(data)
        restored = decompress(result)
        
        for i, item in enumerate(restored):
            assert item["val"] == "abcdefghijklmnopqrstuvwxyz"[i]

    def test_collision_values_refs(self):
        """Test strings that look like equivalence refs."""
        data = [
            {"val": "#0"},
            {"val": "#1"},
            {"val": "\\#0"},  # Already escaped in input?
            {"val": "##0"},
        ]
        result = compress(data)
        restored = decompress(result)
        
        assert restored[0]["val"] == "#0"
        assert restored[1]["val"] == "#1"
        assert restored[2]["val"] == "\\#0"
        assert restored[3]["val"] == "##0"

    def test_bare_list_roundtrip(self):
        """Test that a top-level list (bare list) is restored as a list."""
        from distill.config import with_config
        
        data = [{"a": 1}, {"a": 2}]
        
        # Force compression even if size increases
        with with_config(fallback_on_increase=False):
            result = compress(data)
            
            # Verify internal flag
            parsed = json.loads(result["compressed"])
            assert parsed["$"].get("_bare") is True
            
            restored = decompress(result)
            assert isinstance(restored, list)
            assert restored == data

    def test_extra_data_preservation(self):
        """Test that extra data in the structure is preserved."""
        data = {
            "meta": {"version": 1.0, "author": "me"},
            "events": [{"id": 1}, {"id": 2}]
        }
        result = compress(data)
        restored = decompress(result)
        
        assert restored["meta"] == {"version": 1.0, "author": "me"}
        assert restored["events"] == [{"id": 1}, {"id": 2}]

    def test_mixed_primitives_in_list(self):
        """Test list with mixed dicts and primitives (should fallback or handle gracefully)."""
        data = [
            {"a": 1},
            123,
            "string",
            None
        ]
        # Schema extraction expects dicts.
        # If mixed, extract_schema returns tuples with MISSING for non-dicts?
        # Or find_array_data might not select it if it's not mostly dicts?
        # Let's see what happens.
        result = compress(data)
        restored = decompress(result)
        
        assert restored == data

    def test_deeply_nested_arrays(self):
        """Test arrays inside arrays."""
        data = {
            "matrix": [
                [{"x": 1}, {"x": 2}],
                [{"x": 3}, {"x": 4}]
            ]
        }
        # find_array_data looks for list of dicts.
        # "matrix" is list of lists.
        # So it won't compress the outer list.
        # It might descend? No, find_array_data is not recursive in that way (it iterates values).
        # So this should be passthrough or fallback.
        result = compress(data)
        restored = decompress(result)
        
        assert restored == data
