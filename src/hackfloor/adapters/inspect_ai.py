"""Experimental adapter for Inspect AI scorers.

Only completion-based scorers that do not require model calls are supported.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from hackfloor.adapters.base import CompletionSubject
from hackfloor.core import TaskRef


def _resolve(result: Any) -> Any:
    """Return a scorer's result, awaiting it when the scorer is async.

    Inspect scorers are coroutines. ``asyncio.run`` cannot be called from a thread that
    already runs an event loop (a notebook, an async test), so in that case the coroutine
    runs on a short-lived worker thread instead.
    """
    if not inspect.isawaitable(result):
        return result

    async def _await() -> Any:
        return await result

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_await())
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _await()).result()


class InspectScorerSubject(CompletionSubject):
    """Score Inspect AI samples using an Inspect scorer."""

    framework = "inspect_ai"

    def __init__(
        self,
        scorer: Any,
        samples: Iterable[Any],
        *,
        name: str | None = None,
        gold_template: str = "{answer}",
        reward_min: float = 0.0,
        reward_max: float = 1.0,
    ) -> None:
        try:
            from inspect_ai.model import (
                ChatMessageAssistant,
                ChatMessageUser,
                ModelOutput,
            )
            from inspect_ai.scorer import Score, Target
            from inspect_ai.solver import TaskState
        except ImportError as exc:
            raise ImportError(
                "the Inspect AI adapter needs `pip install hackfloor[inspect-ai]`"
            ) from exc

        if not callable(scorer):
            raise TypeError("scorer must be an Inspect AI scorer callable")

        registry_info = getattr(scorer, "__registry_info__", None)
        scorer_name = getattr(registry_info, "name", getattr(scorer, "__name__", "custom"))

        if scorer_name.startswith("inspect_ai/model_graded_"):
            raise ValueError(
                f"{scorer_name} is a model-graded scorer and is not supported "
                "by the Inspect AI adapter"
            )

        self.scorer = scorer
        self.samples = list(samples)
        if not self.samples:
            raise ValueError("the Inspect AI sample collection is empty")

        self._Score = Score
        self._Target = Target
        self._TaskState = TaskState
        self._ChatMessageAssistant = ChatMessageAssistant
        self._ChatMessageUser = ChatMessageUser
        self._ModelOutput = ModelOutput

        super().__init__(
            name=name or f"inspect_ai:{scorer_name}",
            gold_template=gold_template,
            reward_min=reward_min,
            reward_max=reward_max,
        )

    def tasks(self) -> list[TaskRef]:
        return [
            TaskRef(
                id=str(sample.id if sample.id is not None else index),
                meta={"index": index, "metadata": sample.metadata or {}},
            )
            for index, sample in enumerate(self.samples)
        ]

    def _sample(self, task: TaskRef) -> Any:
        return self.samples[task.meta["index"]]

    def reference(self, task: TaskRef) -> str | None:
        target = self._sample(task).target
        if not target:
            return None
        if isinstance(target, str):
            return target
        return "\n".join(str(item) for item in target)

    def prompt(self, task: TaskRef) -> str | None:
        sample_input = self._sample(task).input
        if isinstance(sample_input, str):
            return sample_input

        return "\n".join(
            str(message.content) for message in sample_input if hasattr(message, "content")
        )

    def score(self, task: TaskRef, completion: str) -> float:
        sample = self._sample(task)

        if isinstance(sample.input, str):
            input_messages = [self._ChatMessageUser(content=sample.input)]
        else:
            input_messages = list(sample.input)

        messages = [
            *input_messages,
            self._ChatMessageAssistant(content=completion),
        ]

        state = self._TaskState(
            model="mockllm/model",
            sample_id=sample.id if sample.id is not None else task.id,
            epoch=1,
            input=sample.input,
            messages=messages,
            target=self._Target(sample.target),
            output=self._ModelOutput(completion=completion),
            metadata=sample.metadata or {},
        )

        result = _resolve(self.scorer(state, state.target))

        if result is None:
            raise ValueError("Inspect scorer returned no score")

        if not isinstance(result, self._Score):
            raise TypeError(f"Inspect scorer returned {type(result).__name__}, expected Score")

        value = result.value

        # Convert Inspect AI's standard categorical verdicts to numeric rewards.
        if isinstance(value, str):
            categorical_values = {
                "C": 1.0,
                "I": 0.0,
            }
            if value in categorical_values:
                return categorical_values[value]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"Inspect scorer returned an unsupported reward value: {value!r}")

        return float(value)

    def describe(self) -> dict[str, Any]:
        return {
            **super().describe(),
            "experimental": True,
            "scorer": getattr(
                getattr(self.scorer, "__registry_info__", None),
                "name",
                getattr(self.scorer, "__name__", "custom"),
            ),
        }
