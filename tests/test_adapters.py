"""Framework adapters, without the frameworks installed.

The environment below is a duck-typed stand-in with OpenEnv's reset/step shape, so the
adapter logic runs in every CI job. tests/test_integrations.py repeats these checks against
the real verifiers, OpenEnv and reasoning-gym packages when they are installed.
"""

import math
from types import SimpleNamespace

import jsonschema
import pytest

from hackfloor import scan
from hackfloor.adapters import CompletionSubject, OpenEnvSubject, resolve_subject
from hackfloor.adapters.base import CompletionSubject as Base
from hackfloor.card import build_card, card_schema
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


def test_openenv_subject_rejects_multi_step_episodes():
    class Endless(StandInEnv):
        def step(self, action):
            return SimpleNamespace(reward=1.0, done=False)

    subject = OpenEnvSubject(
        lambda: Endless(False), [{"index": 0}], make_action=str, gold=lambda e, o, k: e.target
    )
    attempt = subject.grade(subject.tasks()[0], "21")
    assert not attempt.well_formed
    assert "single-step" in attempt.error


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


@pytest.mark.parametrize("lenient", [True, False])
def test_adapter_cards_validate_against_the_card_schema(lenient):
    subject = OpenEnvSubject(
        lambda: StandInEnv(lenient),
        [{"index": i} for i in range(len(QUESTIONS))],
        make_action=str,
        gold=lambda env, obs, kwargs: env.target,
    )
    card = build_card(scan(subject, ScanConfig(replays=1)))
    assert card["subject"]["framework"] == "openenv"
    jsonschema.validate(card, card_schema())
