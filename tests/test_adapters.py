"""Framework adapters, without the frameworks installed.

The environment below is a duck-typed stand-in with OpenEnv's reset/step shape, so the
adapter logic runs in every CI job. tests/test_integrations.py repeats these checks against
the real verifiers, OpenEnv and reasoning-gym packages when they are installed.
"""

import math
from types import SimpleNamespace

import pytest

from hackfloor import scan
from hackfloor.adapters import CompletionSubject, OpenEnvSubject, resolve_subject
from hackfloor.adapters.base import CompletionSubject as Base
from hackfloor.core import TaskRef
from hackfloor.scan import ScanConfig

QUESTIONS = [(12, 9), (30, 4), (7, 25), (16, 16), (41, 2), (8, 19)]


class StandInEnv:
    def __init__(self, lenient: bool):
        self.lenient = lenient
        self.target = None
        self.closed = False

    def reset(self, index: int = 0, **_):
        a, b = QUESTIONS[index]
        self.target = str(a + b)
        return SimpleNamespace(question=f"What is {a} + {b}?", reward=0.0, done=False)

    def step(self, action):
        reply = action.strip()
        ok = self.target in reply if self.lenient else reply == self.target
        return SimpleNamespace(reward=float(ok), done=True)

    def close(self):
        self.closed = True


def make_subject(lenient: bool) -> OpenEnvSubject:
    return OpenEnvSubject(
        lambda: StandInEnv(lenient),
        [{"index": i} for i in range(len(QUESTIONS))],
        make_action=lambda text: text,
        gold=lambda env, obs, kwargs: env.target,
    )


def test_lazy_exports_are_the_classes():
    assert CompletionSubject is Base
    assert OpenEnvSubject.framework == "openenv"


def test_openenv_subject_reads_prompt_and_reference():
    subject = make_subject(lenient=False)
    task = subject.tasks()[0]
    assert subject.prompt(task) == "What is 12 + 9?"
    assert subject.gold(task) == "21"
    assert subject.grade(task, "21").reward == 1.0
    assert subject.grade(task, "").reward == 0.0
    assert subject.answer_visible(task) is False
    assert subject.describe()["experimental"] is True


@pytest.mark.parametrize(("lenient", "verdict"), [(True, "VULNERABLE"), (False, "RESISTED")])
def test_openenv_subject_scan(lenient, verdict):
    result = scan(make_subject(lenient), ScanConfig(replays=1))
    assert result.calibration.sanity == "PASS"
    assert result.verdict == verdict
    dump = {p.probe.id: p for p in result.probes}["HF-DUMP"]
    assert dump.status == ("finding" if lenient else "resisted")


def test_openenv_subject_rejects_episode_that_exceeds_step_limit():
    class Endless(StandInEnv):
        def step(self, action):
            return SimpleNamespace(reward=1.0, done=False)

    subject = OpenEnvSubject(
        lambda: Endless(False), [{"index": 0}], make_action=str, gold=lambda e, o, k: e.target
    )
    attempt = subject.grade(subject.tasks()[0], "21")
    assert not attempt.well_formed
    assert "configured number of steps" in attempt.error


def test_openenv_subject_without_gold_cannot_calibrate():
    subject = OpenEnvSubject(lambda: StandInEnv(False), [{"index": 0}], make_action=str)
    task = subject.tasks()[0]
    assert subject.answer_visible(task) is None
    with pytest.raises(ValueError, match="no reference"):
        subject.gold(task)


def test_completion_subject_turns_exceptions_into_errors():
    class Broken(Base):
        def tasks(self):
            return [TaskRef("0")]

        def reference(self, task):
            return "1"

        def prompt(self, task):
            return "?"

        def score(self, task, completion):
            if completion == "boom":
                raise RuntimeError("grader crashed")
            return float("inf")

    subject = Broken(name="broken")
    crashed = subject.grade(TaskRef("0"), "boom")
    assert crashed.error == "RuntimeError: grader crashed" and math.isnan(crashed.reward)
    assert subject.grade(TaskRef("0"), "x").error == "non-finite reward"


def test_subject_target(tmp_path, monkeypatch):
    (tmp_path / "my_env.py").write_text(
        "from test_adapters import make_subject\n"
        "def build():\n    return make_subject(True)\n"
        "def not_a_subject():\n    return 42\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.syspath_prepend(str(__import__("pathlib").Path(__file__).parent))
    assert resolve_subject("subject:my_env:build").framework == "openenv"
    with pytest.raises(ValueError, match="without a callable"):
        resolve_subject("subject:my_env:not_a_subject")


@pytest.mark.parametrize(
    ("aggregation", "expected"),
    [("final", 0.7), ("sum", 1.2)],
)
def test_openenv_subject_supports_multi_step_episodes(aggregation, expected):
    actions = []

    class MultiStepEnv:
        def reset(self, **kwargs):
            self.step_count = 0
            return SimpleNamespace(reward=0.0, done=False)

        def step(self, action):
            actions.append(action)
            self.step_count += 1
            rewards = [0.2, 0.3, 0.7]
            return SimpleNamespace(
                reward=rewards[self.step_count - 1],
                done=self.step_count == 3,
            )

        def close(self):
            pass

    subject = OpenEnvSubject(
        MultiStepEnv,
        [{"index": 0}],
        make_action=str,
        steps_per_episode=3,
        noop_action="WAIT",
        reward_aggregation=aggregation,
    )

    attempt = subject.grade(subject.tasks()[0], "42")

    assert attempt.well_formed
    assert attempt.reward == pytest.approx(expected)
    assert actions == ["WAIT", "WAIT", "42"]


def test_openenv_subject_reads_the_reward_from_a_client_step_result():
    class ClientEnv:
        def reset(self, **kwargs):
            return SimpleNamespace(reward=0.0, done=False)

        def step(self, action):
            observation = SimpleNamespace(reward=None, done=True)
            return SimpleNamespace(observation=observation, reward=1.0, done=True)

    subject = OpenEnvSubject(ClientEnv, [{}], make_action=str)
    attempt = subject.grade(subject.tasks()[0], "x")
    assert attempt.well_formed
    assert attempt.reward == 1.0


@pytest.mark.parametrize(("aggregation", "expected"), [("final", 1.0), ("sum", 1.0)])
def test_openenv_subject_counts_a_missing_intermediate_reward_as_zero(aggregation, expected):
    class QuietEnv:
        def reset(self, **kwargs):
            self.step_count = 0

        def step(self, action):
            self.step_count += 1
            reward = None if self.step_count < 3 else 1.0
            return SimpleNamespace(reward=reward, done=self.step_count == 3)

    subject = OpenEnvSubject(
        QuietEnv,
        [{}],
        make_action=str,
        steps_per_episode=3,
        noop_action="WAIT",
        reward_aggregation=aggregation,
    )
    attempt = subject.grade(subject.tasks()[0], "x")
    assert attempt.well_formed
    assert attempt.reward == pytest.approx(expected)


def test_openenv_subject_reports_a_missing_final_reward():
    class SilentEnv:
        def reset(self, **kwargs):
            pass

        def step(self, action):
            return SimpleNamespace(reward=None, done=True)

    subject = OpenEnvSubject(SilentEnv, [{}], make_action=str)
    attempt = subject.grade(subject.tasks()[0], "x")
    assert not attempt.well_formed
    assert "no reward" in attempt.error


def test_openenv_subject_reports_an_episode_that_ends_early():
    class ShortEnv:
        def reset(self, **kwargs):
            pass

        def step(self, action):
            return SimpleNamespace(reward=1.0, done=True)

    subject = OpenEnvSubject(
        ShortEnv, [{}], make_action=str, steps_per_episode=3, noop_action="WAIT"
    )
    attempt = subject.grade(subject.tasks()[0], "x")
    assert not attempt.well_formed
    assert "ended before the completion action" in attempt.error


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"steps_per_episode": 0}, "positive integer"),
        ({"steps_per_episode": True}, "positive integer"),
        ({"steps_per_episode": 2}, "noop_action is required"),
        ({"reward_aggregation": "mean"}, "'sum' or 'final'"),
    ],
)
def test_openenv_subject_validates_the_episode_configuration(kwargs, message):
    with pytest.raises(ValueError, match=message):
        OpenEnvSubject(StandInEnv, [{}], make_action=str, **kwargs)


def test_openenv_multi_step_scan_separates_a_lenient_grader_from_an_exact_one():
    class Episode(StandInEnv):
        def __init__(self, lenient):
            super().__init__(lenient)
            self.steps = 0

        def step(self, action):
            self.steps += 1
            if self.steps < 3:
                return SimpleNamespace(reward=0.0, done=False)
            return super().step(action)

    def build(lenient):
        return OpenEnvSubject(
            lambda: Episode(lenient),
            [{"index": i} for i in range(len(QUESTIONS))],
            make_action=str,
            gold=lambda env, obs, kwargs: env.target,
            steps_per_episode=3,
            noop_action="WAIT",
        )

    lenient = scan(build(True), ScanConfig(replays=1))
    exact = scan(build(False), ScanConfig(replays=1))
    assert lenient.calibration.sanity == exact.calibration.sanity == "PASS"
    assert lenient.verdict == "VULNERABLE"
    assert exact.verdict == "RESISTED"
