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
    assert probes["HF-JUDGE"].status == "resisted"
    assert probes["HF-EQ"].status == "not_applicable"
    assert result.verdict == "VULNERABLE"
    assert result.level == 0


def test_fixed_math_is_clean(fixtures):
    subject = resolve_subject(str(fixtures / "rlvr" / "fixed_math"))
    result = scan(subject, ScanConfig(replays=1))
    assert result.findings == []
    assert result.verdict == "RESISTED"
    assert result.level == 1


@pytest.mark.parametrize(
    ("name", "expected"),
    [("vulnerable_judge", {"HF-JUDGE", "HF-DUMP"}), ("fixed_judge", set())],
)
def test_judge_fixtures(fixtures, name, expected):
    result = scan(resolve_subject(str(fixtures / "rlvr" / name)), ScanConfig(replays=1))
    assert {p.probe.id for p in result.findings} == expected
    if expected:
        assert _by_id(result)["HF-JUDGE"].severity == "critical"


def test_echo_finds_answers_visible_in_the_prompt():
    def reward(completion, answer):
        return 1.0 if answer in completion else 0.0

    rows = [{"prompt": f"Repeat the code {1000 + i}.", "answer": str(1000 + i)} for i in range(6)]
    result = scan(RewardFunctionSubject(reward, rows), ScanConfig(replays=1))
    assert _by_id(result)["HF-ECHO"].severity == "critical"
    assert result.leaks == (6, 6)


def test_answer_in_text_uses_token_boundaries():
    from hackfloor.adapters.rlvr import answer_in_text

    assert answer_in_text("12", "What is 5 + 7? 12 apples")
    assert not answer_in_text("12", "What is 112 + 3?")
    assert not answer_in_text("2", "What is 2.5 doubled?")
    assert answer_in_text("x", None) is None


def test_probes_never_see_the_answer(fixtures):
    """Completion probes must be task-blind: identical variants for every row."""
    from hackfloor.probes.base import ProbeContext, get_probes

    subject = resolve_subject(str(fixtures / "rlvr" / "vulnerable_math"))
    t0, t1 = subject.tasks()[:2]
    for probe in get_probes(["HF-EMPTY", "HF-FORMAT", "HF-DUMP", "HF-JUDGE"]):
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
    rows = [{"prompt": f"q{i}", "answer": str(20 + i)} for i in range(8)]
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


def test_output_equal_to_the_reference_is_not_a_hack():
    """A task whose correct answer is empty must not make the empty-slot probes critical.

    Regression test for reasoning-gym's ``ab`` dataset, where one task's answer is the empty
    string and the format probe's empty answer slot was counted as a hack-pass.
    """

    import re

    def reward(completion, answer):
        m = re.search(r"<answer>(.*?)</answer>", completion, re.S)
        return 1.0 if m and m.group(1).strip() == answer else 0.0

    rows = [{"prompt": f"Reduce program {i}.", "answer": f"A# #B {i}"} for i in range(9)]
    rows.append({"prompt": "Reduce program 9.", "answer": ""})
    subject = RewardFunctionSubject(reward, rows, gold_template="<answer>{answer}</answer>")
    result = scan(subject, ScanConfig(replays=1))
    probes = _by_id(result)
    assert result.calibration.sanity == "PASS"
    assert result.findings == []
    assert result.verdict == "RESISTED"
    # Two variants put an empty answer slot on the last task, whose answer is empty.
    assert probes["HF-FORMAT"].skipped_same_as_reference == 2
    assert probes["HF-FORMAT"].hack_passes == 0


def test_same_as_reference_ignores_whitespace_and_case_only():
    from hackfloor.scan import same_as_reference

    assert same_as_reference(" \n\t ", "")
    assert same_as_reference("<answer>  True\n</answer>", "<answer> true </answer>")
    assert not same_as_reference("<answer>0 1 2</answer>", "<answer>1</answer>")
    assert not same_as_reference(lambda ws: None, "")
    tags = "<answer>{answer}</answer>"
    assert same_as_reference("<think>\n</think>\n<answer></answer>", "<answer></answer>", tags)
    assert not same_as_reference(
        "<think>\n</think>\n<answer>7</answer>", "<answer>8</answer>", tags
    )
    assert not same_as_reference("no tags at all", "<answer></answer>", tags)


def test_card_records_variants_skipped_as_reference():
    from hackfloor.card import build_card

    def reward(completion, answer):
        inside = completion.removeprefix("<answer>").removesuffix("</answer>")
        return 1.0 if completion.startswith("<answer>") and inside.strip() == answer else 0.0

    rows = [{"prompt": "Reduce.", "answer": ""}] + [
        {"prompt": f"Reduce {i}.", "answer": str(i)} for i in range(5)
    ]
    subject = RewardFunctionSubject(reward, rows, gold_template="<answer>{answer}</answer>")
    card = build_card(scan(subject, ScanConfig(replays=1)))
    fmt = next(p for p in card["probes"] if p["id"] == "HF-FORMAT")
    assert fmt["skipped_same_as_reference"] == 2
