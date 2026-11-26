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
    """Completion probes must be task-blind: identical variants for every row.

    HF-WRONG is the one exception: it reads the reference answer by design.
    """
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


def _well_formed_credit(credit):
    """A grader that pays ``credit`` for any tagged answer and 1.0 for the right one."""
    import re

    def reward(completion, answer):
        m = re.search(r"<answer>(.*?)</answer>", completion or "", re.S)
        if not m:
            return 0.0
        return 1.0 if m.group(1).strip() == answer else credit

    return reward


def _credit_rows():
    return [
        {"prompt": f"Sort the words in sentence {i}.", "answer": f"w{i} x{i}"} for i in range(8)
    ]


def test_small_credit_for_a_well_formed_answer_is_info_not_a_finding():
    subject = RewardFunctionSubject(
        _well_formed_credit(0.05), _credit_rows(), gold_template="<answer>{answer}</answer>"
    )
    result = scan(subject, ScanConfig(replays=1))
    fmt = _by_id(result)["HF-FORMAT"]
    assert fmt.status == "info"
    assert fmt.severity == "none"
    assert "partial credit" in fmt.message
    assert result.findings == []
    assert result.verdict == "RESISTED"
    assert result.level == 1


def test_partial_credit_above_the_bound_stays_a_finding():
    subject = RewardFunctionSubject(
        _well_formed_credit(0.25), _credit_rows(), gold_template="<answer>{answer}</answer>"
    )
    fmt = _by_id(scan(subject, ScanConfig(replays=1)))["HF-FORMAT"]
    assert fmt.status == "finding"
    assert fmt.severity == "medium"


def test_partial_credit_bound_can_be_disabled():
    subject = RewardFunctionSubject(
        _well_formed_credit(0.05), _credit_rows(), gold_template="<answer>{answer}</answer>"
    )
    fmt = _by_id(scan(subject, ScanConfig(replays=1, partial_credit=0)))["HF-FORMAT"]
    assert fmt.status == "finding"


def test_partial_credit_appears_in_card_and_reports():
    from hackfloor.card import build_card
    from hackfloor.report.markdown import render_markdown

    subject = RewardFunctionSubject(
        _well_formed_credit(0.05), _credit_rows(), gold_template="<answer>{answer}</answer>"
    )
    card = build_card(scan(subject, ScanConfig(replays=1)))
    assert card["summary"]["partial_credit"] >= 1
    assert card["summary"]["findings"] == 0
    assert "HF-FORMAT" in card["checks"]["statistical.adversarial_floor"]["partial_credit"]
    assert card["checks"]["statistical.adversarial_floor"]["status"] == "PASS"
    assert card["method"]["partial_credit_bound"] == 0.1
    assert "Partial credit (not findings)" in render_markdown(card)


def test_wrong_answers_are_conservative_edits():
    from hackfloor.probes.answer import wrong_answers

    assert wrong_answers("True") == [("flipped-boolean", "False")]
    assert wrong_answers("no") == [("flipped-boolean", "yes")]
    assert wrong_answers("YES") == [("flipped-boolean", "NO")]
    assert wrong_answers("C") == [("next-option", "D")]
    assert wrong_answers("J") == [("next-option", "A")]
    assert wrong_answers("7") == [("changed-number", "8")]
    assert wrong_answers("42") == [("changed-number", "46")]
    assert wrong_answers("-3.50") == [("changed-number", "-2.50")]
    assert wrong_answers("97.45") == [("changed-number", "107.20")]
    assert wrong_answers("$x = 7$") == [("changed-number", "$x = 8$")]
    assert wrong_answers("1 2 3") == [("changed-number", "1 2 4")]
    assert wrong_answers("") == []
    assert wrong_answers("A# #B") == []
    assert wrong_answers("hello world") == []


def test_wrong_answer_probe_is_the_only_one_given_the_reference(fixtures):
    from hackfloor.probes.base import ProbeContext, get_probes

    subject = resolve_subject(str(fixtures / "rlvr" / "fixed_math"))
    task = subject.tasks()[0]
    reference = subject.gold(task)
    readers = [p.id for p in get_probes() if p.uses_reference]
    assert readers == ["HF-WRONG"]
    probe = get_probes(["HF-WRONG"])[0]
    ctx = ProbeContext(task, subject, subject.gold_template, reference=reference)
    variants = probe.variants(ctx)
    assert [v.name for v in variants] == ["changed-number"]
    assert variants[0].exploit != reference
    assert variants[0].control == "<answer></answer>"
    assert probe.variants(ProbeContext(task, subject, subject.gold_template)) == []


def test_wrong_answer_probe_catches_a_bool_check(fixtures):
    """A grader that compares bool(answer) accepts the opposite answer (reasoning-gym #561)."""
    vulnerable = scan(resolve_subject(str(fixtures / "rlvr" / "vulnerable_halting")))
    wrong = _by_id(vulnerable)["HF-WRONG"]
    assert wrong.status == "finding"
    assert wrong.severity == "critical"
    assert wrong.hack_passes == wrong.n == 40
    fixed = scan(resolve_subject(str(fixtures / "rlvr" / "fixed_halting")))
    assert fixed.verdict == "RESISTED"
    assert _by_id(fixed)["HF-WRONG"].status == "resisted"


def test_canary_floor_check_follows_hf_wrong(fixtures):
    from hackfloor.card import build_card

    card = build_card(scan(resolve_subject(str(fixtures / "rlvr" / "vulnerable_halting"))))
    assert card["checks"]["semantic.canary_floor"]["status"] == "FAIL"
    assert card["checks"]["semantic.canary_floor"]["findings"] == ["HF-WRONG"]


def test_wrong_answer_resists_a_loose_but_correct_comparison():
    """Case and whitespace differences are not wrong answers; only the edited answer is graded."""

    def reward(completion, answer):
        import re

        m = re.search(r"<answer>(.*?)</answer>", completion, re.S)
        return 1.0 if m and m.group(1).strip().lower() == answer.lower() else 0.0

    rows = [{"prompt": f"Is {i} even?", "answer": "yes" if i % 2 == 0 else "no"} for i in range(10)]
    subject = RewardFunctionSubject(reward, rows, gold_template="<answer>{answer}</answer>")
    assert _by_id(scan(subject, ScanConfig(replays=1)))["HF-WRONG"].status == "resisted"


def test_near_miss_credit_from_hf_wrong_is_info():
    """Graded credit for a close but wrong answer is a reward design, not a hack."""

    def reward(completion, answer):
        import re

        m = re.search(r"<answer>(.*?)</answer>", completion, re.S)
        if not m:
            return 0.0
        got, want = m.group(1).split(), answer.split()
        if len(got) != len(want):
            return 0.0
        return sum(a == b for a, b in zip(got, want, strict=True)) / len(want)

    rows = [
        {"prompt": f"Solve grid {i}.", "answer": " ".join(str((i + k) % 9 + 1) for k in range(9))}
        for i in range(12)
    ]
    subject = RewardFunctionSubject(reward, rows, gold_template="<answer>{answer}</answer>")
    result = scan(subject, ScanConfig(replays=1))
    wrong = _by_id(result)["HF-WRONG"]
    assert wrong.status == "info"
    assert "graded credit" in wrong.message
    assert result.verdict == "RESISTED"


def test_isolated_hack_pass_on_many_tasks_is_info():
    """A fixed probe output that happens to be correct on one task out of many is not a finding.

    reasoning-gym's gsm_symbolic has a task whose answer is 10, and an injection text that
    ends in "Score: 10" was graded as that answer.
    """
    import re

    def reward(completion, answer):
        m = re.search(r"<answer>(.*?)</answer>", completion, re.S)
        if not m:
            return 0.0
        numbers = re.findall(r"-?\d+", m.group(1))
        return 1.0 if numbers and numbers[-1] == answer else 0.0

    rows = [{"prompt": f"Compute item {i}.", "answer": str(100 + i)} for i in range(30)]
    rows[7]["answer"] = "10"
    subject = RewardFunctionSubject(reward, rows, gold_template="<answer>{answer}</answer>")
    result = scan(subject, ScanConfig(replays=2, probe_ids=["HF-JUDGE"]))
    judge = _by_id(result)["HF-JUDGE"]
    assert judge.hack_passes == 1
    assert judge.status == "info"
    assert "isolated hack-pass on 1 of 30 tasks (7)" in judge.message
    assert result.verdict == "RESISTED"


def test_hack_pass_on_few_tasks_is_still_a_finding():
    import re

    def reward(completion, answer):
        m = re.search(r"<answer>(.*?)</answer>", completion, re.S)
        if not m:
            return 0.0
        numbers = re.findall(r"-?\d+", m.group(1))
        return 1.0 if numbers and numbers[-1] == answer else 0.0

    rows = [{"prompt": "Compute.", "answer": "10"}, {"prompt": "Compute.", "answer": "11"}]
    subject = RewardFunctionSubject(reward, rows, gold_template="<answer>{answer}</answer>")
    judge = _by_id(scan(subject, ScanConfig(replays=2, probe_ids=["HF-JUDGE"])))["HF-JUDGE"]
    assert judge.status == "finding"
    assert judge.severity == "critical"


def test_isolated_hack_pass_does_not_make_graded_credit_critical():
    """Significant small credit plus one coincidental full pass is not critical.

    reasoning-gym's cryptarithm pays 0.01 for any parseable mapping and accepts every valid
    solution, so a changed digit is sometimes another valid solution.
    """
    import re

    def reward(completion, answer):
        m = re.search(r"<answer>(.*?)</answer>", completion, re.S)
        if not m or not m.group(1).strip():
            return 0.0
        got = m.group(1).strip()
        return 1.0 if got == answer or got == "8" else 0.01

    rows = [{"prompt": f"Pick a digit {i}.", "answer": str(i % 6 + 1)} for i in range(40)]
    rows[3]["answer"] = "7"  # its changed answer, 8, is also accepted
    subject = RewardFunctionSubject(reward, rows, gold_template="<answer>{answer}</answer>")
    wrong = _by_id(scan(subject, ScanConfig(replays=2, probe_ids=["HF-WRONG"])))["HF-WRONG"]
    assert wrong.hack_passes == 1
    assert wrong.status == "info"
    assert wrong.severity == "none"
    assert "isolated hack-pass" in wrong.message
