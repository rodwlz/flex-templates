"""
Cross-platform test runner.  Works on Windows, macOS, and Linux.

Usage:
    python run_test.py                 # run all tests
    python run_test.py -v              # verbose, one line per test
    python run_test.py -x              # stop at first failure
    python run_test.py -k "back"       # only tests with "back" in the name
    python run_test.py tests/test_router.py    # one specific file
"""
import sys

import pytest


def main() -> int:
    return pytest.main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
