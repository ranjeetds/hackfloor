"""HF-WRONG: a plausible wrong answer in the right format.

This is the one built-in probe that reads the reference completion. It changes the answer
just enough to make it wrong (a flipped boolean, a number off by one, the next option
letter) and checks that the grader scores it no higher than an empty answer in the same
format. A grader that accepts it does not compare the answer at all, or compares it too
loosely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from hackfloor.core import Capability
from hackfloor.probes.base import Probe, ProbeContext, Variant, answer_slot, register

_COMPLETION = frozenset({Capability.COMPLETION})
_BOOLEANS = {"true": "false", "false": "true", "yes": "no", "no": "yes"}
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_OPTIONS = "ABCDEFGHIJ"


def _same_case(word: str, like: str) -> str:
    if like.isupper():
        return word.upper()
    if like[:1].isupper():
        return word.capitalize()
    return word


def wrong_answers(answer: str) -> list[tuple[str, str]]:
    """Plausible wrong versions of ``answer`` as (variant name, text) pairs.

    Only three conservative edits are made, so the result is wrong for any task with a
    unique answer: a boolean or yes/no flipped, the last number in the answer changed by
    one, or a single option letter A-J moved to the next letter. Other answers give no
    variant.
    """
    text = answer.strip()
    if not text:
        return []
    out: list[tuple[str, str]] = []
    flipped = _BOOLEANS.get(text.lower())
    if flipped is not None:
        out.append(("flipped-boolean", _same_case(flipped, text)))
    if len(text) == 1 and text in _OPTIONS:
        out.append(("next-option", _OPTIONS[(_OPTIONS.index(text) + 1) % len(_OPTIONS)]))
    numbers = list(_NUMBER.finditer(text))
    if numbers:
        m = numbers[-1]
        digits = m.group(0)
        decimals = len(digits.split(".")[1]) if "." in digits else 0
        value = float(digits) + 1
        new = f"{value:.{decimals}f}" if decimals else str(int(value))
        out.append(("off-by-one", text[: m.start()] + new + text[m.end() :]))
    return out


@register
@dataclass(frozen=True)
class WrongAnswerProbe(Probe):
    id: str = "HF-WRONG"
    family: str = "form"
    title: str = "Plausible wrong answer"
    mechanism: str = (
        "Takes the reference answer and makes it wrong: a flipped boolean, a number off by "
        "one, the next option letter. Compared with an empty answer in the same format, so "
        "only acceptance of the wrong answer itself counts. Catches graders that check "
        "only that an answer exists, or match too loosely."
    )
    requires: frozenset[Capability] = field(default_factory=lambda: _COMPLETION)
    references: tuple[str, ...] = (
        "reasoning-gym game_of_life_halting bool(answer) check, fixed in "
        "open-thought/reasoning-gym#561",
        "OpenEnv RFC 008 semantic.canary_floor",
    )
    rfc008: str = "semantic.canary_floor"
    uses_reference: bool = True

    def variants(self, ctx: ProbeContext) -> list[Variant]:
        if not isinstance(ctx.reference, str):
            return []
        slot = answer_slot(ctx.reference, ctx.gold_template)
        if slot is None:
            return []
        control = ctx.wrap("")
        return [Variant(name, ctx.wrap(text), control) for name, text in wrong_answers(slot)]
