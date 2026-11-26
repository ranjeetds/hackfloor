"""The same judge-based reward with the injection path closed.

The response is parsed first; only the extracted answer reaches the judge, inside a fenced
block, and the judge's score is read from its own output position, not from anywhere in
the prompt. The judge is the same deterministic stub, so this is a teaching fixture, not a
claim about real LLM judges.
"""

import re

_TAG = re.compile(r"<answer>(.*?)</answer>", re.S)


def stub_judge(answer_block: str, reference: str) -> int:
    """Compare the fenced answer with the reference. Ignores any text outside the fence."""
    match = re.fullmatch(r"```\n(.*)\n```", answer_block, re.S)
    content = match.group(1).strip() if match else ""
    return 10 if content == reference else 0


def reward(prompts, completions, answer, **kwargs):
    out = []
    for completion, ref in zip(completions, answer):
        blocks = _TAG.findall(completion)
        extracted = blocks[-1].strip() if blocks else ""
        if not re.fullmatch(r"[+-]?\d+", extracted):
            out.append(0.0)
            continue
        out.append(stub_judge(f"```\n{extracted}\n```", ref) / 10)
    return out
