#!/usr/bin/env python
"""
Run all verification checks before release.

This script runs tests, checks code quality, and verifies the package
is ready for PyPI upload.

Usage:
    python scripts/verify_release.py
"""

import subprocess
import sys
import os
from pathlib import Path


def run_check(name: str, cmd: str) -> bool:
    """Run a check and return True if it passes."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"Command: {cmd}")
    print('='*60)

    result = subprocess.run(cmd, shell=True, cwd=Path(__file__).parent.parent)

    if result.returncode != 0:
        print(f"\n[FAILED] {name}")
        return False

    print(f"\n[PASSED] {name}")
    return True


def main():
    """Run all verification checks."""
    print("\n" + "="*60)
    print("DISTILL Release Verification")
    print("="*60)

    checks = [
        ("Unit Tests", "python -m pytest tests/ -v --tb=short"),
        ("Edge Case Tests", "python -m pytest tests/test_edge_cases.py -v"),
        ("Integration Tests", "python -m pytest tests/test_integration.py -v"),
    ]

    # Optional checks (may not be installed)
    optional_checks = [
        ("Type Checking (mypy)", "python -m mypy distill/ --ignore-missing-imports"),
        ("Linting (ruff)", "python -m ruff check distill/"),
        ("Formatting (black)", "python -m black --check distill/"),
    ]

    failed = []
    passed = []
    skipped = []

    # Run required checks
    for name, cmd in checks:
        if run_check(name, cmd):
            passed.append(name)
        else:
            failed.append(name)

    # Run optional checks
    for name, cmd in optional_checks:
        try:
            if run_check(name, cmd):
                passed.append(name)
            else:
                failed.append(name)
        except Exception as e:
            print(f"\n[SKIPPED] {name} - {e}")
            skipped.append(name)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if passed:
        print(f"\n[PASSED] ({len(passed)}):")
        for name in passed:
            print(f"    {name}")

    if skipped:
        print(f"\n[SKIPPED] ({len(skipped)}):")
        for name in skipped:
            print(f"    {name}")

    if failed:
        print(f"\n[FAILED] ({len(failed)}):")
        for name in failed:
            print(f"    {name}")
        print(f"\n{'='*60}")
        print("RESULT: NOT READY FOR RELEASE")
        print("Fix the above failures before publishing.")
        print('='*60)
        sys.exit(1)
    else:
        print(f"\n{'='*60}")
        print("RESULT: READY FOR RELEASE")
        print('='*60)
        sys.exit(0)


if __name__ == "__main__":
    main()
