"""Checks with type-aware comparisons. Prints a sentinel only after every check passed."""

import os
import sys

sys.path.insert(0, os.getcwd())

from slug import slugify  # noqa: E402

CASES = [
    ("Hello World", "hello-world"),
    ("  Reward  Hacking! ", "reward-hacking"),
    ("RFC 008, Level 2", "rfc-008-level-2"),
]
for text, expected in CASES:
    result = slugify(text)
    if type(result) is not str or result != expected:
        sys.stderr.write(f"FAIL {text!r}: got {result!r}\n")
        sys.exit(1)

print(f"CHECKS_PASSED {len(CASES)}")
