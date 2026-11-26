import pytest

from hackfloor import scan
from hackfloor.adapters import RewardFunctionSubject, resolve_subject
from hackfloor.adapters.rlvr import detect_flavor
from hackfloor.scan import ScanConfig


def _by_id(result):
    return {p.probe.id: p for p in result.probes}


def test_vulnerable_math_is_flagged(fixtures):
    subject = resolve_subject(str(fixtures / "rlvr" / "vulnerable_math"))
    result = scan(subject, ScanConfig(replays=1))
    probes = _by_id(result)
    assert result.calibration.sanity == "PASS"
    assert probes["HF-DUMP"].status == "finding"
    assert probes["HF-DUMP"].severity == "critical"
    assert probes["HF-DUMP"].hack_passes == 40
    assert probes["HF-FORMAT"].status == "finding"
    assert probes["HF-FORMAT"].severity == "medium"
    assert probes["HF-FORMAT"].delta_mean == pytest.approx(0.2)
    assert probes["HF-EMPTY"].status == "resisted"
    assert probes["HF-EQ"].status == "not_applicable"
    assert result.verdict == "VULNERABLE"
    assert result.level == 0


def test_fixed_math_is_clean(fixtures):
    subject = resolve_subject(str(fixtures / "rlvr" / "fixed_math"))
    result = scan(subject, ScanConfig(replays=1))
    assert result.findings == []
    assert result.verdict == "RESISTED"
    assert result.level == 1


def test_probes_never_see_the_answer(fixtures):
    """Completion probes must be task-blind: identical variants for every row."""
    from hackfloor.probes.base import ProbeContext, get_probes

    subject = resolve_subject(str(fixtures / "rlvr" / "vulnerable_math"))
    t0, t1 = subject.tasks()[:2]
    for probe in get_probes(["HF-EMPTY", "HF-FORMAT", "HF-DUMP"]):
        v0 = [v.exploit for v in probe.variants(ProbeContext(t0, subject, subject.gold_template))]
        v1 = [v.exploit for v in probe.variants(ProbeContext(t1, subject, subject.gold_template))]
        assert v0 == v1


def test_flavor_detection():
    def plain(completion, answer):
        return 0.0

    def verl(data_source, solution_str, ground_truth, extra_info=None):
        return 0.0

    def trl(completions, **kwargs):
        return [0.0]

    assert detect_flavor(plain) == "plain"
    assert detect_flavor(verl) == "verl"
    assert detect_flavor(trl) == "trl"


@pytest.mark.parametrize("flavor", ["verl", "trl"])
def test_verl_and_trl_signatures(flavor):
    def verl(data_source, solution_str, ground_truth, extra_info=None):
        return {"score": float(ground_truth in solution_str)}

    def trl(prompts, completions, answer, **kwargs):
        return [float(a in c) for c, a in zip(completions, answer, strict=False)]

    fn = verl if flavor == "verl" else trl
    rows = [{"prompt": f"q{i}", "answer": str(10 + i)} for i in range(8)]
    subject = RewardFunctionSubject(fn, rows, flavor=flavor)
    assert subject.flavor == flavor
    result = scan(subject, ScanConfig(replays=1))
    assert {p.probe.id for p in result.findings} == {"HF-DUMP"}


def test_crashing_reward_is_reported_not_hidden():
    def fragile(completion, answer):
        if not completion.strip():
            raise ValueError("empty")
        return float(completion == answer)

    rows = [{"answer": str(i)} for i in range(5)]
    result = scan(RewardFunctionSubject(fragile, rows), ScanConfig(replays=1))
    assert result.errors
    assert result.level == 0


def test_uncalibrated_when_reference_does_not_beat_null():
    rows = [{"answer": str(i)} for i in range(5)]
    result = scan(RewardFunctionSubject(lambda c, a: 0.5, rows), ScanConfig(replays=1))
    assert result.calibration.sanity == "FAIL"
    assert result.verdict == "UNCALIBRATED"
    assert result.level is None


def test_module_target_requires_data(tmp_path):
    with pytest.raises(ValueError):
        resolve_subject("some_module:reward")
