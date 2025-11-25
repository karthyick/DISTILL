"""Final verification script."""
import json
import time
from distill import compress, decompress

# Test cases
test_cases = [
    # Basic
    {"events": [{"a": 1}, {"a": 2}]},
    
    # Types
    {"items": [{"s": "str", "i": 42, "f": 3.14, "b": True, "n": None}]},
    
    # Repeated (uses equivalence)
    {"events": [{"t": "x", "p": "y"}] * 5},
    
    # Unicode
    {"items": [{"text": "Hello 世界 🌍"}]},
    
    # Reserved strings
    {"items": [{"a": "null", "b": "true", "c": "#0"}]},
    
    # Nested
    {"items": [{"nested": {"deep": [1, 2, 3]}}]},
    
    # Large
    {"items": [{"i": i, "s": f"value_{i}"} for i in range(100)]},
]

print("DISTILL Verification")
print("=" * 50)

all_passed = True
for i, data in enumerate(test_cases):
    try:
        result = compress(data)
        restored = decompress(result)
        
        if restored == data:
            status = "[PASS]"
            reduction = result["meta"]["reduction_percent"]
            print(f"Test {i+1}: {status} ({reduction:.1f}% reduction)")
        else:
            status = "[FAIL] - Data mismatch"
            print(f"Test {i+1}: {status}")
            print(f"  Original: {json.dumps(data)[:100]}")
            print(f"  Restored: {json.dumps(restored)[:100]}")
            all_passed = False
    except Exception as e:
        print(f"Test {i+1}: [FAIL] - {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

print("=" * 50)
print("All tests passed!" if all_passed else "Some tests failed!")
