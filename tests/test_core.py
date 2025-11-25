"""
Tests for core compression modules.

New 3-layer architecture:
- schema: Native schema extraction
- huffman: Dictionary encoding (a-z codes)
- equivalence: Equivalence partitioning (#N refs)
"""

import pytest
from distill.core.schema import extract_schema, find_array_data, reconstruct_objects
from distill.core.huffman import DictionaryEncoder, build_codebook
from distill.core.equivalence import EquivalencePartitioner, apply_equivalence
from distill.core.tokenizer import count_tokens, get_token_stats


class TestSchema:
    """Tests for schema extraction."""

    def test_extract_schema_basic(self):
        """Test basic schema extraction."""
        data = [
            {"name": "Alice", "role": "admin"},
            {"name": "Bob", "role": "viewer"}
        ]

        schema, tuples = extract_schema(data)

        assert "name" in schema
        assert "role" in schema
        assert len(tuples) == 2

    def test_extract_schema_sorted(self):
        """Test schema keys are sorted."""
        data = [
            {"z": 1, "a": 2, "m": 3},
            {"z": 4, "a": 5, "m": 6}
        ]

        schema, tuples = extract_schema(data)

        assert schema == ["a", "m", "z"]

    def test_extract_schema_handles_missing_keys(self):
        """Test extraction handles objects with different keys."""
        from distill.core.schema import MISSING

        data = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob"}  # no email
        ]

        schema, tuples = extract_schema(data)

        assert "name" in schema
        assert "email" in schema
        # Bob's email should be MISSING sentinel (not None, which is a valid value)
        email_idx = schema.index("email")
        assert isinstance(tuples[1][email_idx], type(MISSING))

    def test_find_array_data_top_level(self):
        """Test finding top-level array."""
        data = [{"a": 1}, {"a": 2}]

        wrapper_key, array_data, extra = find_array_data(data)

        assert wrapper_key is None
        assert array_data == data
        assert extra is None

    def test_find_array_data_wrapped(self):
        """Test finding wrapped array."""
        data = {
            "items": [{"a": 1}, {"a": 2}],
            "meta": {"count": 2}
        }

        wrapper_key, array_data, extra = find_array_data(data)

        assert wrapper_key == "items"
        assert len(array_data) == 2
        assert extra == {"meta": {"count": 2}}

    def test_reconstruct_objects(self):
        """Test reconstructing objects from schema and tuples."""
        schema = ["name", "role"]
        tuples = [
            ["Alice", "admin"],
            ["Bob", "viewer"]
        ]

        objects = reconstruct_objects(schema, tuples)

        assert len(objects) == 2
        assert objects[0]["name"] == "Alice"
        assert objects[0]["role"] == "admin"


class TestDictionaryEncoder:
    """Tests for dictionary encoding."""

    def test_build_dictionary(self):
        """Test dictionary is built correctly."""
        encoder = DictionaryEncoder()
        values = ["INFO", "INFO", "INFO", "WARN", "ERROR"]

        dictionary = encoder.build_dictionary(values)

        # INFO is most frequent, should get 'a'
        assert "a" in dictionary
        # Values are now JSON-serialized for type preservation
        # String "INFO" becomes '"INFO"' when flattened
        assert dictionary["a"] == '"INFO"'

    def test_encode_value(self):
        """Test encoding single values."""
        encoder = DictionaryEncoder()
        encoder.build_dictionary(["click", "view", "click", "click"])

        encoded = encoder.encode_value("click")
        assert encoded == "a"  # most frequent

        encoded = encoder.encode_value("view")
        assert encoded == "b"

    def test_encode_tuple(self):
        """Test encoding tuples."""
        encoder = DictionaryEncoder()
        encoder.build_dictionary(["click", "home", "view", "about"])

        # All values in dict -> concatenated
        encoded = encoder.encode_tuple(["click", "home"])
        assert len(encoded) == 2
        assert all(c.islower() for c in encoded)

    def test_decode_tuple(self):
        """Test decoding tuples."""
        encoder = DictionaryEncoder()
        encoder.build_dictionary(["click", "home"])

        encoded = encoder.encode_tuple(["click", "home"])
        decoded = encoder.decode_tuple(encoded, 2)

        assert decoded == ["click", "home"]

    def test_short_values_not_encoded(self):
        """Test that single-char values aren't encoded (no benefit)."""
        encoder = DictionaryEncoder()
        values = ["a", "b", "c", "a", "a", "a"]

        dictionary = encoder.build_dictionary(values)

        # Single chars shouldn't be in dictionary
        assert "a" not in dictionary.values()


class TestEquivalence:
    """Tests for equivalence partitioning."""

    def test_find_equivalences_basic(self):
        """Test finding equivalence classes."""
        partitioner = EquivalencePartitioner(min_occurrences=2)
        encoded = ["abc", "def", "abc", "abc", "ghi"]

        equivalences, final_data = partitioner.find_equivalences(encoded)

        # "abc" appears 3 times, should get #0
        assert "#0" in equivalences
        assert equivalences["#0"] == "abc"
        assert final_data.count("#0") == 3

    def test_find_equivalences_respects_min(self):
        """Test min_occurrences is respected."""
        partitioner = EquivalencePartitioner(min_occurrences=3)
        encoded = ["abc", "def", "abc"]  # abc only appears twice

        equivalences, final_data = partitioner.find_equivalences(encoded)

        # Should not create equivalence class
        assert len(equivalences) == 0
        assert "#0" not in final_data

    def test_expand_equivalences(self):
        """Test expanding equivalence references."""
        partitioner = EquivalencePartitioner()
        partitioner.set_equivalences({"#0": "abc", "#1": "def"})

        data = ["#0", "xyz", "#1", "#0"]
        expanded = partitioner.expand_equivalences(data)

        assert expanded == ["abc", "xyz", "def", "abc"]

    def test_apply_equivalence_function(self):
        """Test apply_equivalence convenience function."""
        encoded = ["abc", "abc", "def"]

        equivalences, final_data = apply_equivalence(encoded, min_occurrences=2)

        assert "#0" in equivalences
        assert equivalences["#0"] == "abc"


class TestTokenizer:
    """Tests for token counting."""

    def test_count_tokens_string(self):
        """Test counting tokens in string."""
        tokens = count_tokens("Hello world")
        assert tokens > 0

    def test_count_tokens_dict(self):
        """Test counting tokens in dict."""
        tokens = count_tokens({"key": "value"})
        assert tokens > 0

    def test_count_tokens_list(self):
        """Test counting tokens in list."""
        tokens = count_tokens([1, 2, 3])
        assert tokens > 0

    def test_get_token_stats(self):
        """Test token statistics calculation."""
        original = '{"users": [{"name": "Alice"}, {"name": "Bob"}]}'
        compressed = '{"$":{"schema":["name"]},"users":["Alice","Bob"]}'

        stats = get_token_stats(original, compressed)

        assert "original_tokens" in stats
        assert "compressed_tokens" in stats
        assert "reduction_percent" in stats

    def test_longer_text_more_tokens(self):
        """Test that longer text has more tokens."""
        short = "hello"
        long = "hello world this is a longer string with more tokens"

        short_tokens = count_tokens(short)
        long_tokens = count_tokens(long)

        assert long_tokens > short_tokens


class TestIntegration:
    """Integration tests for core modules working together."""

    def test_full_pipeline(self):
        """Test the full compression pipeline."""
        # Original data
        data = [
            {"type": "click", "page": "home"},
            {"type": "click", "page": "home"},
            {"type": "view", "page": "about"},
        ]

        # Step 1: Schema extraction
        schema, tuples = extract_schema(data)
        assert len(schema) == 2
        assert len(tuples) == 3

        # Step 2: Dictionary encoding
        encoder = DictionaryEncoder()
        all_values = [v for t in tuples for v in t]
        encoder.build_dictionary(all_values)

        encoded_tuples = [encoder.encode_tuple(t) for t in tuples]
        assert all(isinstance(e, str) for e in encoded_tuples)

        # Step 3: Equivalence partitioning
        partitioner = EquivalencePartitioner(min_occurrences=2)
        equivalences, final_data = partitioner.find_equivalences(encoded_tuples)

        # First two records are identical, should be grouped
        assert "#0" in final_data

    def test_pipeline_roundtrip(self):
        """Test full pipeline with roundtrip."""
        original = [
            {"name": "Alice", "role": "admin"},
            {"name": "Bob", "role": "admin"},
            {"name": "Charlie", "role": "user"},
        ]

        # Compress
        schema, tuples = extract_schema(original)
        encoder = DictionaryEncoder()
        all_values = [v for t in tuples for v in t]
        encoder.build_dictionary(all_values)
        encoded = [encoder.encode_tuple(t) for t in tuples]
        partitioner = EquivalencePartitioner(min_occurrences=2)
        partitioner.find_equivalences(encoded)

        # Decompress
        expanded = partitioner.expand_equivalences(encoded)
        decoded = [encoder.decode_tuple(e, len(schema)) for e in expanded]
        restored = reconstruct_objects(schema, decoded)

        assert len(restored) == len(original)
        for orig, rest in zip(original, restored):
            assert orig == rest
