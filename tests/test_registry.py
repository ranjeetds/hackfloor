from dataclasses import dataclass, field

import pytest

from hackfloor import Capability, Probe, Variant, get_probes, register, scan
from hackfloor.adapters import RewardFunctionSubject
from hackfloor.probes import BUILTIN_PROBES
from hackfloor.scan import ScanConfig

BUILTIN_IDS = {
    "HF-EMPTY",
    "HF-FORMAT",
    "HF-DUMP",
    "HF-EQ",
    "HF-EXIT",
    "HF-CONFTEST",
    "HF-TESTEDIT",
    "HF-REWARDFILE",
}


def test_builtins_registered_with_metadata():
    probes = {p.id: p for p in get_probes(plugins=False)}
    assert set(probes) >= BUILTIN_IDS
    assert {p.id for p in BUILTIN_PROBES} == BUILTIN_IDS
    for probe in probes.values():
        assert probe.family in {"form", "tamper", "contain", "leak", "judge"}
        assert probe.title and probe.mechanism and probe.references
        assert probe.requires


def test_unknown_probe_id_is_an_error():
    with pytest.raises(KeyError):
        get_probes(["HF-NOPE"])


def test_selection_is_case_insensitive():
    assert [p.id for p in get_probes(["hf-dump"])] == ["HF-DUMP"]


@dataclass(frozen=True)
class ShoutProbe(Probe):
    id: str = "X-SHOUT"
    family: str = "form"
    title: str = "Shouting"
    mechanism: str = "Answers in capitals."
    requires: frozenset = field(default_factory=lambda: frozenset({Capability.COMPLETION}))
    references: tuple = ("test",)

    def variants(self, ctx):
        return [Variant("shout", "LOUD")]


def test_register_adds_and_rejects_duplicates():
    from hackfloor.probes import base

    try:
        register(ShoutProbe)
        assert "X-SHOUT" in {p.id for p in get_probes(plugins=False)}

        @dataclass(frozen=True)
        class Impostor(ShoutProbe):
            pass

        with pytest.raises(ValueError):
            register(Impostor())
    finally:
        base._REGISTRY.pop("X-SHOUT", None)


def test_third_party_probe_runs_through_the_engine():
    def reward(completion, answer):
        return 1.0 if completion.isupper() or completion == answer else 0.0

    rows = [{"answer": str(i)} for i in range(6)]
    subject = RewardFunctionSubject(reward, rows, name="shout")
    result = scan(subject, ScanConfig(replays=1), probes=[ShoutProbe()])
    (probe,) = result.probes
    assert probe.status == "finding"
    assert probe.severity == "critical"
    assert probe.hack_passes == 6
