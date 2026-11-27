import pytest

from hackfloor import scan
from hackfloor.adapters import resolve_subject
from hackfloor.core import Capability
from hackfloor.scan import ScanConfig

CASES = {
    "vulnerable_pytest": {
        "findings": {
            "HF-EQ",
            "HF-CONFTEST",
            "HF-TESTEDIT",
            "HF-REWARDFILE",
            "HF-SKIPTEST",
            "HF-LOOKUP",
        },
        "level": 0,
    },
    "fixed_pytest": {"findings": set(), "level": 1},
    "vulnerable_script": {"findings": {"HF-EQ", "HF-EXIT"}, "level": 0},
    "fixed_script": {"findings": set(), "level": 1},
    "vulnerable_leaky": {"findings": {"HF-ANSWERKEY", "HF-GITLEAK"}, "level": 0},
    "fixed_leaky": {"findings": set(), "level": 1},
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_task_fixture(fixtures, name):
    subject = resolve_subject(str(fixtures / "tasks" / name))
    result = scan(subject, ScanConfig(replays=1))
    assert result.calibration.sanity == "PASS", result.calibration.reasons
    found = {p.probe.id for p in result.findings}
    assert found == CASES[name]["findings"]
    assert all(p.severity == "critical" for p in result.findings)
    assert result.level == CASES[name]["level"]
    for p in result.probes:
        if p.status not in ("not_applicable", "error"):
            assert p.basis == "deterministic-replay"
    assert not [p for p in result.probes if p.status == "error"]


def test_capabilities_follow_the_config(fixtures):
    pytest_caps = resolve_subject(str(fixtures / "tasks" / "vulnerable_pytest")).capabilities()
    script_caps = resolve_subject(str(fixtures / "tasks" / "vulnerable_script")).capabilities()
    assert Capability.VISIBLE_TESTS in pytest_caps
    assert Capability.REWARD_FILE_WRITABLE in pytest_caps
    assert Capability.VISIBLE_TESTS not in script_caps
    assert Capability.REWARD_FILE_WRITABLE not in script_caps


def test_each_attempt_gets_a_fresh_sandbox(fixtures):
    subject = resolve_subject(str(fixtures / "tasks" / "vulnerable_pytest"))
    (task,) = subject.tasks()

    def prewrite(ws):
        ws.write_reward_file(1.0)

    assert subject.grade(task, prewrite).reward == 1.0
    assert subject.grade(task, subject.null(task)).reward == 0.0


def test_suite_directory_collects_tasks(fixtures):
    subject = resolve_subject(str(fixtures / "tasks"))
    assert len(subject.tasks()) == 6


def test_leak_checks_on_the_card(fixtures):
    from hackfloor.card import build_card

    for name, status in (("vulnerable_leaky", "FAIL"), ("fixed_leaky", "PASS")):
        result = scan(resolve_subject(str(fixtures / "tasks" / name)), ScanConfig(replays=1))
        check = build_card(result)["checks"]["semantic.no_solution_leakage"]
        assert check["status"] == status


def test_setup_runs_in_every_sandbox(fixtures):
    subject = resolve_subject(str(fixtures / "tasks" / "vulnerable_leaky"))
    (task,) = subject.tasks()
    with subject.sandbox_preview(task) as ws:
        assert (ws.path / ".git").is_dir()
        assert (ws.root / ".oracle" / "slug.py").is_file()


def test_failed_setup_is_an_error_not_a_reward(tmp_path, fixtures):
    import shutil

    task = tmp_path / "broken"
    shutil.copytree(fixtures / "tasks" / "fixed_script", task)
    config = (task / "hackfloor.toml").read_text()
    config = config.replace(
        'entry_functions = ["slugify"]',
        'entry_functions = ["slugify"]\nsetup = ["{python}", "-c", "import sys; sys.exit(1)"]',
    )
    (task / "hackfloor.toml").write_text(config)
    subject = resolve_subject(str(task))
    (ref,) = subject.tasks()
    attempt = subject.grade(ref, subject.gold(ref))
    assert attempt.error and "setup failed" in attempt.error
