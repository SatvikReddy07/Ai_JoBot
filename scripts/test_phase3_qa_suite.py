"""Compatibility entrypoint for safe, isolated Phase 3 / 3.1 regression checks.

Replaces the old real-profile-dependent script that edited application documents
and notification records in the active database. The pytest fixtures isolate all
writes in temporary storage. No external application or account is accessed.
"""
from pathlib import Path
import subprocess
import sys


def run_qa_tests():
    root = Path(__file__).resolve().parents[1]
    return subprocess.run([sys.executable, "-m", "pytest", "backend/tests/test_phase3.py",
        "backend/tests/test_matcher.py", "-q", "-p", "no:cacheprovider"], cwd=root).returncode


if __name__ == "__main__":
    raise SystemExit(run_qa_tests())
