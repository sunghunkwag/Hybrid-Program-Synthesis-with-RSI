import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from systemtest.validators import validate_algo_program, validate_code, validate_program


def test_validate_code_allows_basic_function():
    code = textwrap.dedent(
        """
        def solve(x):
            total = 0
            for i in range(3):
                total = total + i
            return total + x
        """
    )
    ok, err = validate_code(code)
    assert ok, err


def test_validate_code_blocks_imports():
    code = textwrap.dedent(
        """
        import os
        def solve(x):
            return x
        """
    )
    ok, _ = validate_code(code)
    assert not ok


def test_validate_program_blocks_loops():
    code = textwrap.dedent(
        """
        def solve(x):
            for i in range(2):
                x = x + i
            return x
        """
    )
    ok, _ = validate_program(code)
    assert not ok


def test_validate_algo_program_allows_loops():
    code = textwrap.dedent(
        """
        def run(inp):
            total = 0
            for x in inp:
                total = total + x
            return total
        """
    )
    ok, err = validate_algo_program(code)
    assert ok, err
