"""A deliberately weak True/False reward. Do not copy this into a real environment."""

import re


def reward(completion: str, answer: str) -> float:
    match = re.search(r"<answer>(.*?)</answer>", completion, re.S)
    if match is None:
        return 0.0
    # Bug: bool("False") is True, so any non-empty answer matches any non-empty reference.
    return 1.0 if bool(match.group(1).strip()) == bool(answer) else 0.0
