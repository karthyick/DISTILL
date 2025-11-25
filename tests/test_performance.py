"""
Performance tests for DISTILL.
"""

import pytest
import time
import json
from distill import compress, decompress

class TestPerformance:
    
    def test_large_dataset_performance(self):
        """Test compression speed on large dataset."""
        # Generate 10k items
        data = [{"id": i, "type": "click", "page": "home"} for i in range(10000)]
        
        start = time.time()
        result = compress(data)
        duration = time.time() - start
        
        # Should be reasonably fast (e.g. < 1s for 10k items)
        # On this machine it might vary, but let's set a loose bound
        assert duration < 2.0, f"Compression took too long: {duration:.4f}s"
        
        # Decompression speed
        start = time.time()
        restored = decompress(result)
        duration = time.time() - start
        
        assert duration < 2.0, f"Decompression took too long: {duration:.4f}s"
        assert len(restored) == 10000

    def test_deep_nesting_performance(self):
        """Test performance with deep nesting."""
        from distill.config import with_config
        
        deep = {"level": 0}
        current = deep
        for i in range(100):
            current["child"] = {"level": i}
            current = current["child"]
            
        start = time.time()
        # Increase max depth for this test
        with with_config(max_depth=200):
            result = compress(deep)
        duration = time.time() - start
        
        assert duration < 0.5, f"Deep nesting compression took too long: {duration:.4f}s"

    def test_compression_ratio(self):
        """Test that compression actually compresses repetitive data."""
        data = [{"type": "click", "page": "home"} for _ in range(1000)]
        original_size = len(json.dumps(data))
        
        result = compress(data)
        compressed_size = len(result["compressed"])
        
        ratio = original_size / compressed_size
        assert ratio > 5.0, f"Compression ratio too low: {ratio:.2f}x"
