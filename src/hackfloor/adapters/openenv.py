"""Adapter for OpenEnv environments (``openenv.core.env_server.interfaces``).

Experimental. Each grade builds a fresh environment from ``env_factory``, calls
``reset(**task_kwargs)``, then ``step(make_action(action))`` once, or, for a scripted
multi-step episode (``steps_per_episode > 1``), ``steps_per_episode - 1`` times with the
caller's ``noop_action`` followed by one step with the completion. The reward is read from
the returned observation (``obs.reward``), or from the step result when it carries one.
``reward_aggregation`` is ``"final"`` (the last step's reward) or ``"sum"`` (all steps; a
step that returns no reward before the last counts as 0). Environments reached over HTTP
or in a container are out of scope for this adapter.

OpenEnv environments usually do not reveal the reference before a step, so the caller
supplies ``gold(env, observation, task_kwargs) -> str`` (for example, reading the entry the
environment just drew).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Literal

from hackfloor.adapters.base import CompletionSubject
from hackfloor.core import TaskRef


def _default_observe(obs: Any) -> str | None:
    for attr in ("prompt", "question", "text", "message"):
        value = getattr(obs, attr, None)
        if isinstance(value, str):
            return value
    return None


class OpenEnvSubject(CompletionSubject):
    framework = "openenv"

    def __init__(
        self,
        env_factory: Callable[[], Any],
        tasks: Sequence[dict[str, Any]],
        *,
        make_action: Callable[[str], Any],
        gold: Callable[[Any, Any, dict[str, Any]], str] | None = None,
        observe: Callable[[Any], str | None] = _default_observe,
        name: str = "openenv",
        reward_min: float = 0.0,
        reward_max: float = 1.0,
        steps_per_episode: int = 1,
        noop_action: str | None = None,
        reward_aggregation: Literal["sum", "final"] = "final",
    ) -> None:
        super().__init__(name=name, reward_min=reward_min, reward_max=reward_max)

        if not tasks:
            raise ValueError("pass at least one set of reset() keyword arguments")
        if (
            isinstance(steps_per_episode, bool)
            or not isinstance(steps_per_episode, int)
            or steps_per_episode < 1
        ):
            raise ValueError("steps_per_episode must be a positive integer")
        if steps_per_episode > 1 and noop_action is None:
            raise ValueError("noop_action is required for multi-step episodes")
        if reward_aggregation not in ("sum", "final"):
            raise ValueError("reward_aggregation must be 'sum' or 'final'")

        self.env_factory = env_factory
        self.task_kwargs = [dict(t) for t in tasks]
        self.make_action = make_action
        self.gold_fn = gold
        self.observe = observe
        self.steps_per_episode = steps_per_episode
        self.noop_action = noop_action
        self.reward_aggregation = reward_aggregation
        self._first: dict[int, tuple[str | None, str | None]] = {}

    def tasks(self) -> list[TaskRef]:
        return [TaskRef(id=str(i), meta={"index": i}) for i in range(len(self.task_kwargs))]

    def _close(self, env: Any) -> None:
        close = getattr(env, "close", None)
        if callable(close):
            close()

    def _peek(self, task: TaskRef) -> tuple[str | None, str | None]:
        i = task.meta["index"]
        if i not in self._first:
            env = self.env_factory()
            try:
                obs = env.reset(**self.task_kwargs[i])
                ref = self.gold_fn(env, obs, self.task_kwargs[i]) if self.gold_fn else None
                self._first[i] = (self.observe(obs), None if ref is None else str(ref))
            finally:
                self._close(env)
        return self._first[i]

    def reference(self, task: TaskRef) -> str | None:
        return self._peek(task)[1]

    def prompt(self, task: TaskRef) -> str | None:
        return self._peek(task)[0]

    def score(self, task: TaskRef, completion: str) -> float:
        env = self.env_factory()
        rewards: list[float] = []
        last = self.steps_per_episode - 1
        try:
            env.reset(**self.task_kwargs[task.meta["index"]])
            actions = [self.noop_action] * last + [completion]
            for index, action in enumerate(actions):
                result = env.step(self.make_action(action))
                obs = getattr(result, "observation", None)
                reward = getattr(result, "reward", None)
                if reward is None and obs is not None:  # a client StepResult
                    reward = getattr(obs, "reward", None)
                if reward is None:
                    if index == last:
                        raise ValueError("the step returned no reward")
                    reward = 0.0  # intermediate steps often carry no reward
                rewards.append(float(reward))
                done = getattr(result, "done", getattr(obs, "done", True))
                if done:
                    if index != last:
                        raise ValueError("the episode ended before the completion action")
                    break
            else:
                raise ValueError("the episode did not end after the configured number of steps")
        finally:
            self._close(env)
        return sum(rewards) if self.reward_aggregation == "sum" else rewards[-1]

    def describe(self) -> dict[str, Any]:
        return {
            **super().describe(),
            "experimental": True,
            "steps_per_episode": self.steps_per_episode,
            "reward_aggregation": self.reward_aggregation,
        }
