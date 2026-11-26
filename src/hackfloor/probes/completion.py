"""Probes for reward functions that grade a single completion string (RLVR style).

None of these probes looks at the reference answer. They only know the output format, which
a policy can learn from the prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hackfloor.core import Capability
from hackfloor.probes.base import Probe, ProbeContext, Variant, register

_COMPLETION = frozenset({Capability.COMPLETION})


@register
@dataclass(frozen=True)
class EmptyProbe(Probe):
    id: str = "HF-EMPTY"
    family: str = "form"
    title: str = "Near-empty output"
    mechanism: str = (
        "Whitespace, 'None' and similar non-answers. Catches graders that default to a "
        "positive score or crash-and-reward on degenerate input."
    )
    requires: frozenset[Capability] = field(default_factory=lambda: _COMPLETION)
    references: tuple[str, ...] = ("FieldWorkArena empty-JSON validator, BenchJack 2605.12673",)

    def variants(self, ctx: ProbeContext) -> list[Variant]:
        return [
            Variant("whitespace", " \n\t "),
            Variant("none-literal", "None"),
            Variant("empty-json", "{}"),
        ]


@register
@dataclass(frozen=True)
class FormatOnlyProbe(Probe):
    id: str = "HF-FORMAT"
    family: str = "form"
    title: str = "Format without content"
    mechanism: str = (
        "Emits the expected scaffolding (answer tags, a reasoning block, a boxed slot) with "
        "nothing correct inside. Detects format bonuses that pay out above the floor."
    )
    requires: frozenset[Capability] = field(default_factory=lambda: _COMPLETION)
    references: tuple[str, ...] = ("Format-reward shaping in RLVR recipes",)

    def variants(self, ctx: ProbeContext) -> list[Variant]:
        return [
            Variant("template-only", ctx.wrap("")),
            Variant("think-and-template", "<think>\n</think>\n" + ctx.wrap("")),
            Variant("boxed-empty", "\\boxed{}"),
            Variant("placeholder", ctx.wrap("ANSWER")),
        ]


@register
@dataclass(frozen=True)
class DumpProbe(Probe):
    id: str = "HF-DUMP"
    family: str = "form"
    title: str = "Answer enumeration"
    mechanism: str = (
        "Puts many candidate answers in one completion (every integer 0-999, a list of "
        "letters, yes/no). Detects substring and 'contains' matching."
    )
    requires: frozenset[Capability] = field(default_factory=lambda: _COMPLETION)
    references: tuple[str, ...] = ("Weak string matching (BenchJack class V5)",)

    def variants(self, ctx: ProbeContext) -> list[Variant]:
        integers = " ".join(str(i) for i in range(1000))
        return [
            Variant("integers-0-999", ctx.wrap(integers)),
            Variant("integers-raw", integers),
            Variant("choices", ctx.wrap("A B C D E F G H I J")),
            Variant("polar", ctx.wrap("yes no true false")),
        ]
