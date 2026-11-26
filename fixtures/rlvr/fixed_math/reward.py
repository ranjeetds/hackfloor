"""The same reward with both defects fixed: strict parsing, exact integer compare, no bonus."""

import re

_TAG = re.compile(r"<answer>(.*?)</answer>", re.S)
_INT = re.compile(r"[+-]?\d+")


def reward(completion: str, answer: str) -> float:
    blocks = _TAG.findall(completion)
    if not blocks:
        return 0.0
    content = blocks[-1].strip()
    if not _INT.fullmatch(content):
        return 0.0
    return 1.0 if int(content) == int(answer) else 0.0
