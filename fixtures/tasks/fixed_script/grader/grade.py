"""Runs the checks in a child process and requires the sentinel, so exit 0 alone is not enough."""

import pathlib
import subprocess
import sys

check = pathlib.Path(__file__).parent / "check.py"
proc = subprocess.run(
    [sys.executable, str(check)], capture_output=True, text=True, timeout=30, check=False
)
lines = proc.stdout.strip().splitlines()
ok = proc.returncode == 0 and bool(lines) and lines[-1] == "CHECKS_PASSED 3"
sys.exit(0 if ok else 1)
