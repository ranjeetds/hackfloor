"""A True/False reward that compares the answer itself."""

import re


def reward(completion: str, answer: str) -> float:
    blocks = re.findall(r"<answer>(.*?)</answer>", completion, re.S)
    if not blocks:
        return 0.0
    return 1.0 if blocks[-1].strip().lower() == answer.strip().lower() else 0.0
