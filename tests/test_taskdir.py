import pytest

from hackfloor import scan
from hackfloor.adapters import resolve_subject
from hackfloor.core import Capability
from hackfloor.scan import ScanConfig

CASES = {
    "vulnerable_pytest": {
        "findings": {"HF-EQ", "HF-CONFTEST", "HF-TESTEDIT", "HF-REWARDFILE"},
        "level": 0,
    },
    "fixed_pytest": {"findings": set(), "level": 1},
    "vulnerable_script": {"findings": {"HF-EQ", "HF-EXIT"}, "level": 0},
    "fixed_script": {"findings": set(), "level": 1},
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
    assert len(subject.tasks()) == 4
