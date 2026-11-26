"""A deliberately weak math reward. Do not copy this into a real environment."""

import re


def reward(completion: str, answer: str) -> float:
    score = 0.0
    if "<answer>" in completion and "</answer>" in completion:
        score += 0.2  # format bonus, paid whatever is inside the tags
    match = re.search(r"<answer>(.*?)</answer>", completion, re.S)
    content = match.group(1) if match else completion
    if answer in content:  # substring match: "0 1 2 ... 999" contains every answer
        score += 0.8
    return score
