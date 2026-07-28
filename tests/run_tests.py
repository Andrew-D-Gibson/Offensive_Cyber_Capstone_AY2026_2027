#!/usr/bin/env python3
"""
run_tests.py

Comprehensive test runner for FAIR-LLM cyber experiment suite.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


async def run_test(module_name, description):
    """Run a test module (as `python -m ...` from the repo root) and report results."""
    print_section(description)
    try:
        result = subprocess.run(
            [sys.executable, "-m", module_name],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        if result.returncode == 0:
            print(f"✓ {description} PASSED")
        else:
            print(f"✗ {description} FAILED (exit code: {result.returncode})")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"✗ {description} TIMEOUT")
        return False
    except Exception as e:
        print(f"✗ {description} ERROR: {e}")
        return False


async def main():
    print_section("FAIR-LLM CYBER EXPERIMENT SUITE")
    print("Running comprehensive test suite...")
    
    tests = [
        ("tests.test_cyber_tools", "Cyber Tools"),
        ("tests.test_single_agent", "Single Agent"),
        ("tests.test_multi_agent", "Multi-Agent"),
    ]
    
    results = {}
    for test_file, description in tests:
        results[description] = await run_test(test_file, description)
    
    print_section("SUMMARY")
    for desc, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {desc}")
    
    all_passed = all(results.values())
    print_section("FINAL RESULT")
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nThe FAIR-LLM cyber experiment suite is ready!")
        print("To run actual experiments with Ollama:")
        print("  python experiment_runner.py --trials 5 --backend ollama")
    else:
        print("✗ SOME TESTS FAILED")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
