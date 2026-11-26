"""A single-step OpenEnv environment for hackfloor's integration tests.

It subclasses OpenEnv's real ``Environment`` base with pydantic ``Action`` and
``Observation`` models. ``lenient=True`` accepts the answer anywhere in the reply, the
pattern of a substring check; ``lenient=False`` requires the reply to be exactly the answer.
"""

from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import Action, Observation, State

from hackfloor.adapters.openenv import OpenEnvSubject

QUESTIONS = [(12, 9), (30, 4), (7, 25), (16, 16), (41, 2), (8, 19)]


class AnswerAction(Action):
    answer: str


class MathObservation(Observation):
    question: str | None = None


class MathEnv(Environment):
    def __init__(self, lenient: bool = False):
        super().__init__()
        self.lenient = lenient
        self.target: str | None = None
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def reset(self, seed=None, episode_id=None, index: int = 0, **kwargs):
        a, b = QUESTIONS[index]
        self.target = str(a + b)
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        return MathObservation(question=f"What is {a} + {b}?", reward=0.0, done=False)

    def step(self, action, timeout_s=None, **kwargs):
        self._state.step_count += 1
        reply = action.answer.strip()
        ok = self.target in reply if self.lenient else reply == self.target
        return MathObservation(question=None, reward=float(ok), done=True)

    @property
    def state(self):
        return self._state


def _subject(lenient: bool) -> OpenEnvSubject:
    return OpenEnvSubject(
        lambda: MathEnv(lenient=lenient),
        [{"index": i} for i in range(len(QUESTIONS))],
        make_action=lambda text: AnswerAction(answer=text),
        gold=lambda env, obs, kwargs: env.target,
        name="openenv-math-lenient" if lenient else "openenv-math-exact",
    )


def vulnerable() -> OpenEnvSubject:
    return _subject(True)


def fixed() -> OpenEnvSubject:
    return _subject(False)
