"""Adapter for single-step OpenEnv environments (``openenv.core.env_server.interfaces``).

Experimental. Each grade builds a fresh environment from ``env_factory``, calls
``reset(**task_kwargs)``, then one ``step(make_action(completion))``, and reads the
reward from the returned observation (``obs.reward``). Multi-step environments, and
environments reached over HTTP or in a container, are out of scope for this adapter.

OpenEnv environments usually do not reveal the reference before a step, so the caller
supplies ``gold(env, observation, task_kwargs) -> str`` (for example, reading the entry the
environment just drew).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

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
    ) -> None:
        super().__init__(name=name, reward_min=reward_min, reward_max=reward_max)
        if not tasks:
            raise ValueError("pass at least one set of reset() keyword arguments")
        self.env_factory = env_factory
        self.task_kwargs = [dict(t) for t in tasks]
        self.make_action = make_action
        self.gold_fn = gold
        self.observe = observe
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
        try:
            env.reset(**self.task_kwargs[task.meta["index"]])
            obs = env.step(self.make_action(completion))
        finally:
            self._close(env)
        reward = getattr(obs, "reward", None)
        if reward is None and hasattr(obs, "observation"):  # a client StepResult
            reward = getattr(obs.observation, "reward", None)
        if reward is None:
            raise ValueError("the step returned no reward")
        if getattr(obs, "done", True) is False:
            raise ValueError("the episode did not end after one step; only single-step envs")
        return float(reward)

    def describe(self) -> dict[str, Any]:
        return {**super().describe(), "experimental": True, "steps_per_episode": 1}
