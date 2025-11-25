"""
Test fixtures for DISTILL.

Provides common test data and fixtures for all tests.
"""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List


# ============================================================================
# Small Dataset Fixtures
# ============================================================================

@pytest.fixture
def simple_list():
    """Simple list with some repeated values."""
    return [
        {"name": "Alice", "role": "admin"},
        {"name": "Bob", "role": "admin"},
        {"name": "Charlie", "role": "viewer"}
    ]


@pytest.fixture
def empty_data():
    """Empty data structures."""
    return {
        "empty_list": [],
        "empty_dict": {},
        "empty_nested": {"items": []}
    }


@pytest.fixture
def single_item():
    """Single item list."""
    return [{"id": 1, "name": "Only Item"}]


# ============================================================================
# Pattern-Rich Fixtures (for MDL rule discovery)
# ============================================================================

@pytest.fixture
def backend_team_data():
    """Data with strong correlations (team -> remote pattern)."""
    return [
        {"id": 1, "team": "backend", "remote": True, "level": "senior"},
        {"id": 2, "team": "backend", "remote": True, "level": "senior"},
        {"id": 3, "team": "backend", "remote": True, "level": "junior"},
        {"id": 4, "team": "frontend", "remote": False, "level": "senior"},
        {"id": 5, "team": "frontend", "remote": False, "level": "mid"},
        {"id": 6, "team": "backend", "remote": True, "level": "senior"},
        {"id": 7, "team": "backend", "remote": True, "level": "mid"},
        {"id": 8, "team": "frontend", "remote": False, "level": "junior"},
    ]


@pytest.fixture
def department_data():
    """Data with department patterns."""
    return [
        {"emp_id": 1, "dept": "Engineering", "location": "NYC", "type": "FTE"},
        {"emp_id": 2, "dept": "Engineering", "location": "NYC", "type": "FTE"},
        {"emp_id": 3, "dept": "Engineering", "location": "NYC", "type": "Contractor"},
        {"emp_id": 4, "dept": "Sales", "location": "LA", "type": "FTE"},
        {"emp_id": 5, "dept": "Sales", "location": "LA", "type": "FTE"},
        {"emp_id": 6, "dept": "Engineering", "location": "NYC", "type": "FTE"},
    ]


# ============================================================================
# Large Dataset Fixtures (for meaningful compression)
# ============================================================================

@pytest.fixture
def large_user_list():
    """Large list with many repeated values."""
    statuses = ["active", "inactive", "pending"]
    roles = ["admin", "user", "viewer", "editor"]
    departments = ["engineering", "sales", "marketing", "support"]

    return [
        {
            "id": i,
            "status": statuses[i % 3],
            "role": roles[i % 4],
            "department": departments[i % 4],
            "verified": i % 2 == 0
        }
        for i in range(100)
    ]


@pytest.fixture
def log_entries():
    """Log-style data with many repeated values."""
    levels = ["INFO", "DEBUG", "WARN", "ERROR"]
    sources = ["api", "db", "cache", "auth"]

    return [
        {
            "timestamp": f"2024-01-{(i % 30) + 1:02d}T10:{i % 60:02d}:00Z",
            "level": levels[i % 4],
            "source": sources[i % 4],
            "message": f"Log message {i}"
        }
        for i in range(50)
    ]


@pytest.fixture
def product_catalog():
    """Product catalog with category patterns."""
    categories = ["Electronics", "Books", "Clothing", "Home"]
    statuses = ["in_stock", "low_stock", "out_of_stock"]

    return [
        {
            "sku": f"SKU-{i:04d}",
            "category": categories[i % 4],
            "status": statuses[i % 3],
            "featured": i % 5 == 0,
            "price": round(10 + (i * 0.5), 2)
        }
        for i in range(80)
    ]


# ============================================================================
# Nested Structure Fixtures
# ============================================================================

@pytest.fixture
def nested_config():
    """Deeply nested configuration data."""
    return {
        "app": {
            "name": "MyApp",
            "version": "1.0.0",
            "config": {
                "server": {
                    "host": "localhost",
                    "port": 8080,
                    "ssl": True
                },
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "mydb"
                },
                "cache": {
                    "host": "localhost",
                    "port": 6379,
                    "ttl": 3600
                }
            }
        }
    }


@pytest.fixture
def nested_array_data():
    """Data with nested arrays."""
    return {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "roles": ["admin", "user"],
                "permissions": ["read", "write", "delete"]
            },
            {
                "id": 2,
                "name": "Bob",
                "roles": ["user"],
                "permissions": ["read"]
            }
        ]
    }


@pytest.fixture
def wrapper_key_data():
    """Data with outer wrapper key."""
    return {
        "response": {
            "data": [
                {"id": 1, "status": "active"},
                {"id": 2, "status": "active"},
                {"id": 3, "status": "inactive"}
            ],
            "meta": {"total": 3}
        }
    }


# ============================================================================
# Edge Case Fixtures
# ============================================================================

@pytest.fixture
def special_characters():
    """Data with special characters."""
    return [
        {"text": "Hello, World!", "emoji": "Test"},
        {"text": "Line1\nLine2", "emoji": "More text"},
        {"text": "Tab\there", "emoji": "End"}
    ]


@pytest.fixture
def numeric_edge_cases():
    """Data with various numeric types."""
    return [
        {"int": 0, "float": 0.0, "neg": -1, "large": 999999999},
        {"int": 42, "float": 3.14159, "neg": -100, "large": 1e10},
        {"int": 1, "float": 0.001, "neg": -0.5, "large": float('inf') if False else 999}
    ]


@pytest.fixture
def null_values():
    """Data with null/None values."""
    return [
        {"id": 1, "value": None, "optional": "present"},
        {"id": 2, "value": "set", "optional": None},
        {"id": 3, "value": None, "optional": None}
    ]


@pytest.fixture
def boolean_data():
    """Data with boolean patterns."""
    return [
        {"id": 1, "active": True, "verified": True},
        {"id": 2, "active": True, "verified": False},
        {"id": 3, "active": False, "verified": True},
        {"id": 4, "active": True, "verified": True},
        {"id": 5, "active": True, "verified": True},
    ]


# ============================================================================
# File I/O Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_json_file(temp_dir, large_user_list):
    """Create a sample JSON file for testing."""
    path = temp_dir / "sample.json"
    with open(path, 'w') as f:
        json.dump(large_user_list, f)
    return path


@pytest.fixture
def sample_distill_file(temp_dir):
    """Create a sample DISTILL file for testing (new JSON format)."""
    from distill import compress

    path = temp_dir / "sample.distill"
    # Create compressed format using actual compress function
    data = [
        {"id": 1, "name": "Alice", "status": "active"},
        {"id": 2, "name": "Bob", "status": "active"},
        {"id": 3, "name": "Charlie", "status": "inactive"}
    ]
    result = compress(data)
    with open(path, 'w') as f:
        f.write(result["compressed"])
    return path


# ============================================================================
# Compressed Format Fixtures
# ============================================================================

@pytest.fixture
def distill_equiv_format():
    """Sample DISTILL equivalence format string (new JSON format)."""
    from distill import compress
    data = [
        {"name": "Alice", "role": "admin"},
        {"name": "Bob", "role": "admin"},
        {"name": "Charlie", "role": "viewer"}
    ]
    result = compress(data)
    return result["compressed"]


@pytest.fixture
def distill_rules_format():
    """Sample DISTILL with patterns format string (new JSON format)."""
    from distill import compress
    data = [
        {"id": 1, "team": "backend", "remote": True},
        {"id": 2, "team": "backend", "remote": True},
        {"id": 3, "team": "frontend", "remote": False}
    ]
    result = compress(data)
    return result["compressed"]


@pytest.fixture
def distill_codebook_format():
    """Sample DISTILL with codebook format string (new JSON format)."""
    from distill import compress
    data = [
        {"msg": "test1", "level": "INFO"},
        {"msg": "test2", "level": "INFO"},
        {"msg": "test3", "level": "DEBUG"}
    ]
    result = compress(data)
    return result["compressed"]


# ============================================================================
# Helper Functions
# ============================================================================

def assert_roundtrip(original: Any, compressed_result: Dict) -> bool:
    """
    Assert that data survives a compress/decompress roundtrip.

    Returns True if roundtrip is lossless.
    """
    from distill import decompress

    if compressed_result.get("meta", {}).get("fallback"):
        # Fallback case - compressed is JSON
        restored = json.loads(compressed_result["compressed"])
    else:
        restored = decompress(compressed_result["compressed"])

    # Deep comparison
    return json.dumps(original, sort_keys=True) == json.dumps(restored, sort_keys=True)


def data_equals_ignoring_order(a: Any, b: Any) -> bool:
    """Compare two data structures ignoring list order."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(data_equals_ignoring_order(a[k], b[k]) for k in a)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        # For list of dicts, compare by content
        return all(any(data_equals_ignoring_order(ai, bj) for bj in b) for ai in a)
    else:
        return a == b
