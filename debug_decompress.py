from distill import decompress
from distill.exceptions import DecompressionError
import pytest

print("Testing decompress(None)...")
try:
    decompress(None)
    print("DID NOT RAISE")
except DecompressionError as e:
    print(f"Caught expected error: {e}")
except Exception as e:
    print(f"Caught UNEXPECTED error: {type(e).__name__}: {e}")

print("\nTesting decompress(123)...")
try:
    decompress(123)
    print("DID NOT RAISE")
except DecompressionError as e:
    print(f"Caught expected error: {e}")
except Exception as e:
    print(f"Caught UNEXPECTED error: {type(e).__name__}: {e}")
