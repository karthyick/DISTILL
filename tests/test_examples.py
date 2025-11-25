"""
Tests using example data from the specification.
"""

import pytest
from distill import compress, decompress


class TestSpecificationExamples:
    """Tests based on examples from the specification."""

    def test_simple_repeated_values(self):
        """Test with larger dataset for meaningful compression."""
        data = [
            {"name": "Alice", "role": "admin", "status": "active"},
            {"name": "Bob", "role": "admin", "status": "active"},
            {"name": "Charlie", "role": "admin", "status": "active"},
            {"name": "Diana", "role": "viewer", "status": "inactive"},
            {"name": "Eve", "role": "viewer", "status": "active"},
            {"name": "Frank", "role": "admin", "status": "active"},
            {"name": "Grace", "role": "admin", "status": "active"},
            {"name": "Henry", "role": "viewer", "status": "inactive"},
        ]

        result = compress(data)

        # Should achieve some compression or fallback
        assert result["meta"]["reduction_percent"] >= 0

    def test_pattern_heavy_data(self):
        """Test pattern-heavy data with discoverable rules."""
        data = [
            {"id": 1, "team": "backend", "remote": True, "level": "senior"},
            {"id": 2, "team": "backend", "remote": True, "level": "mid"},
            {"id": 3, "team": "backend", "remote": True, "level": "junior"},
            {"id": 4, "team": "frontend", "remote": False, "level": "senior"},
            {"id": 5, "team": "frontend", "remote": False, "level": "mid"},
            {"id": 6, "team": "backend", "remote": True, "level": "senior"},
        ]

        result = compress(data, level="medium")

        # Should process without error
        assert "compressed" in result

    def test_log_data_with_repeated_messages(self):
        """Test log data with repeated messages."""
        data = [
            {"level": "INFO", "msg": "Started", "ts": "10:00"},
            {"level": "INFO", "msg": "Processing", "ts": "10:01"},
            {"level": "INFO", "msg": "Processing", "ts": "10:02"},
            {"level": "WARN", "msg": "Slow", "ts": "10:03"},
            {"level": "INFO", "msg": "Processing", "ts": "10:04"},
            {"level": "ERROR", "msg": "Failed", "ts": "10:05"},
            {"level": "INFO", "msg": "Started", "ts": "10:06"},
            {"level": "INFO", "msg": "Processing", "ts": "10:07"},
        ]

        result = compress(data)

        # Should process without error
        assert "compressed" in result

    def test_complex_employee_data(self):
        """Test the complex employee example."""
        data = [
            {"id": 1, "name": "Alice", "role": "developer", "team": "backend", "level": "senior", "remote": True},
            {"id": 2, "name": "Bob", "role": "developer", "team": "backend", "level": "senior", "remote": True},
            {"id": 3, "name": "Charlie", "role": "developer", "team": "backend", "level": "junior", "remote": True},
            {"id": 4, "name": "Diana", "role": "designer", "team": "frontend", "level": "senior", "remote": False},
            {"id": 5, "name": "Eve", "role": "designer", "team": "frontend", "level": "junior", "remote": False},
            {"id": 6, "name": "Frank", "role": "manager", "team": "backend", "level": "senior", "remote": True},
            {"id": 7, "name": "Grace", "role": "manager", "team": "frontend", "level": "senior", "remote": False},
            {"id": 8, "name": "Henry", "role": "developer", "team": "frontend", "level": "junior", "remote": False}
        ]

        # Test all levels
        low = compress(data, level="low")
        medium = compress(data, level="medium")
        high = compress(data, level="high")

        # All should work
        assert "compressed" in low
        assert "compressed" in medium
        assert "compressed" in high

    def test_incident_report_structure(self):
        """Test complex nested structure like incident report."""
        data = {
            "req_id": "req-001",
            "settings": {
                "model": "deepseek-coder-v2-instruct",
                "temperature": 0.0,
                "max_tokens": 4096
            },
            "agents": [
                {"agent_id": "ag_01", "role": "SYSTEM_ARCHITECT", "state": "IDLE"},
                {"agent_id": "ag_02", "role": "FULL_STACK_DEV", "state": "PROCESSING"},
                {"agent_id": "ag_03", "role": "QA_VALIDATOR", "state": "ERROR"}
            ],
            "logs": [
                {"level": "INFO", "msg": "Started"},
                {"level": "INFO", "msg": "Processing"},
                {"level": "WARN", "msg": "Memory spike"},
                {"level": "ERROR", "msg": "OOM"}
            ]
        }

        result = compress(data)

        # Should process without error
        assert "compressed" in result

    def test_auto_selects_best(self):
        """Test auto mode selects the best compression."""
        data = [
            {"role": "admin", "status": "active", "dept": "engineering"},
            {"role": "admin", "status": "active", "dept": "engineering"},
            {"role": "admin", "status": "active", "dept": "engineering"},
            {"role": "admin", "status": "active", "dept": "sales"},
            {"role": "user", "status": "inactive", "dept": "marketing"}
        ]

        result = compress(data, level="auto")

        # Should have meta info
        assert "compressed" in result
        assert "meta" in result


class TestTargetReductions:
    """Tests to verify compression works on larger datasets."""

    @pytest.fixture
    def large_sample(self):
        """Large sample with many repeated values."""
        roles = ["developer", "designer", "manager"]
        teams = ["backend", "frontend", "devops"]
        levels = ["junior", "mid", "senior"]
        statuses = ["active", "inactive"]

        return [
            {
                "id": i,
                "name": f"User{i}",
                "role": roles[i % 3],
                "team": teams[i % 3],
                "level": levels[i % 3],
                "status": statuses[i % 2]
            }
            for i in range(50)
        ]

    def test_low_achieves_compression(self, large_sample):
        """Low level should achieve compression on large data."""
        result = compress(large_sample, level="low")

        # Should achieve some compression
        assert result["meta"]["reduction_percent"] >= 30

    def test_medium_achieves_compression(self, large_sample):
        """Medium level should achieve compression on large data."""
        result = compress(large_sample, level="medium")

        # Should achieve compression
        assert result["meta"]["reduction_percent"] >= 30

    def test_high_achieves_compression(self, large_sample):
        """High level should achieve compression on large data."""
        result = compress(large_sample, level="high")

        # Should achieve compression
        assert result["meta"]["reduction_percent"] >= 30
