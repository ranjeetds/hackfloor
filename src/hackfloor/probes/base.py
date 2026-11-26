"""The probe plugin interface and registry.

A probe is a small, named policy that tries to raise the reward without solving the task.
Each probe yields one or more variants. A variant is an exploit action plus a matched
control action that does the same kind of thing without the exploit payload, so that any
reward difference can be attributed to the mechanism under test.

Third-party probes can be registered with the ``register`` decorator, or exposed through
the ``hackfloor.probes`` entry-point group as a list of Probe instances.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from hackfloor.core import Action, Capability, TaskRef

if TYPE_CHECKING:
    from hackfloor.core import Subject


@dataclass(frozen=True)
class Variant:
    """One concrete attempt. ``control=None`` means: compare against the null policy."""

    name: str
    exploit: Action
    control: Action | None = None


@dataclass(frozen=True)
class ProbeContext:
    """What a probe may know when building variants: the task id and format, never the answer."""

    task: TaskRef
    subject: Subject
    gold_template: str = "{answer}"

    def wrap(self, text: str) -> str:
        """Put ``text`` where the answer would go in the expected output format."""
        return self.gold_template.replace("{answer}", text)


@dataclass(frozen=True)
class Probe:
    """Base class for probes. Subclasses set the metadata and implement ``variants``."""

    id: str = ""
    family: str = ""
    title: str = ""
    mechanism: str = ""
    requires: frozenset[Capability] = field(default_factory=frozenset)
    references: tuple[str, ...] = ()
    rfc008: str = "statistical.adversarial_floor"

    def applies_to(self, capabilities: Iterable[Capability]) -> bool:
        return self.requires.issubset(set(capabilities))

    def variants(self, ctx: ProbeContext) -> list[Variant]:  # pragma: no cover - interface
        raise NotImplementedError


_REGISTRY: dict[str, Probe] = {}


def register(probe: Probe | type[Probe]) -> Probe | type[Probe]:
    """Register a probe instance or class (usable as a class decorator)."""
    instance = probe() if isinstance(probe, type) else probe
    if not instance.id:
        raise ValueError("a probe needs a non-empty id")
    if instance.id in _REGISTRY and type(_REGISTRY[instance.id]) is not type(instance):
        raise ValueError(f"probe id {instance.id!r} is already registered")
    _REGISTRY[instance.id] = instance
    return probe


def _load_entry_points() -> None:
    for ep in entry_points(group="hackfloor.probes"):
        if ep.value.startswith("hackfloor.probes:"):
            continue  # built-ins are imported directly
        loaded = ep.load()
        for probe in loaded if isinstance(loaded, (list, tuple)) else [loaded]:
            register(probe)


def get_probes(ids: Iterable[str] | None = None, *, plugins: bool = True) -> list[Probe]:
    """Return registered probes, optionally filtered by id (case-insensitive)."""
    import hackfloor.probes  # noqa: F401  (registers the built-ins)

    if plugins:
        _load_entry_points()
    probes = sorted(_REGISTRY.values(), key=lambda p: p.id)
    if ids is None:
        return probes
    wanted = {i.upper() for i in ids}
    unknown = wanted - {p.id for p in probes}
    if unknown:
        raise KeyError(f"unknown probe id(s): {', '.join(sorted(unknown))}")
    return [p for p in probes if p.id in wanted]
