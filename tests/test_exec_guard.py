from pathlib import Path
import re


def test_systemtest_has_no_raw_exec_or_eval():
    text = Path("Systemtest.py").read_text(encoding="utf-8")
    assert re.search(r"\bexec\(", text) is None
    assert re.search(r"\beval\(", text) is None
