"""Shared base for adapters whose policy action is one completion string."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any

from hackfloor.adapters.rlvr import answer_in_text
from hackfloor.core import Action, Attempt, Capability, TaskRef


class CompletionSubject(ABC):
    """A subject that scores a single completion per task.

    Subclasses provide the task list, the prompt, the reference answer and a ``score``
    call into the framework's own grader. Everything else (null policy, error handling,
    answer-visibility) is shared.
    """

    framework = "completion"

    def __init__(
        self,
        *,
        name: str,
        gold_template: str = "{answer}",
        reward_min: float = 0.0,
        reward_max: float = 1.0,
    ) -> None:
        self.name = name
        self.gold_template = gold_template
        self.reward_min = reward_min
        self.reward_max = reward_max

    @abstractmethod
    def tasks(self) -> list[TaskRef]: ...

    @abstractmethod
    def reference(self, task: TaskRef) -> str | None:
        """The reference answer, or None when the framework does not expose one."""

    @abstractmethod
    def prompt(self, task: TaskRef) -> str | None: ...

    @abstractmethod
    def score(self, task: TaskRef, completion: str) -> float: ...

    def capabilities(self) -> set[Capability]:
        return {Capability.COMPLETION}

    def gold(self, task: TaskRef) -> Action:
        answer = self.reference(task)
        if answer is None:
            raise ValueError(f"{self.name}: task {task.id} exposes no reference answer")
        return self.gold_template.replace("{answer}", answer)

    def null(self, task: TaskRef) -> Action:
        return ""

    def observation(self, task: TaskRef) -> str | None:
        return self.prompt(task)

    def answer_visible(self, task: TaskRef) -> bool | None:
        answer = self.reference(task)
        return None if answer is None else answer_in_text(answer, self.prompt(task))

    def grade(self, task: TaskRef, action: Action) -> Attempt:
        if not isinstance(action, str):
            raise TypeError(f"{self.framework} subjects grade completion strings only")
        try:
            reward = float(self.score(task, action))
        except Exception as exc:
            return Attempt(reward=float("nan"), error=f"{type(exc).__name__}: {exc}")
        if not math.isfinite(reward):
            return Attempt(reward=reward, error="non-finite reward")
        return Attempt(reward=reward)

    def describe(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "name": self.name,
            "n_tasks": len(self.tasks()),
            "gold_template": self.gold_template,
            "reward_range": [self.reward_min, self.reward_max],
        }
