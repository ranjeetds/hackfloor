"""Adapter for reasoning-gym procedural datasets (``pip install reasoning-gym``).

A completion is scored the way reasoning-gym's own training recipes do: the text inside
``<answer>...</answer>`` is extracted with ``reasoning_gym.utils.extract_answer`` and passed
to the dataset's ``score_answer``. The gold completion wraps the dataset's reference answer
in the same tags.
"""

from __future__ import annotations

from typing import Any

from hackfloor.adapters.base import CompletionSubject
from hackfloor.core import TaskRef

DEFAULT_TEMPLATE = "<answer>{answer}</answer>"


class ReasoningGymSubject(CompletionSubject):
    framework = "reasoning-gym"

    def __init__(
        self,
        dataset: Any,
        *,
        name: str = "reasoning-gym",
        tag: str = "answer",
        gold_template: str = DEFAULT_TEMPLATE,
    ) -> None:
        super().__init__(name=name, gold_template=gold_template)
        self.dataset = dataset
        self.tag = tag
        self.entries = [dataset[i] for i in range(len(dataset))]
        if not self.entries:
            raise ValueError("the dataset is empty")

    @classmethod
    def create(
        cls, dataset_name: str, *, size: int = 20, seed: int = 0, **config: Any
    ) -> ReasoningGymSubject:
        try:
            import reasoning_gym
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise ImportError(
                "the reasoning-gym adapter needs `pip install hackfloor[reasoning-gym]`"
            ) from exc
        dataset = reasoning_gym.create_dataset(dataset_name, size=size, seed=seed, **config)
        return cls(dataset, name=f"reasoning-gym:{dataset_name}")

    def tasks(self) -> list[TaskRef]:
        return [TaskRef(id=str(i), meta={"index": i}) for i in range(len(self.entries))]

    def _entry(self, task: TaskRef) -> dict[str, Any]:
        return self.entries[task.meta["index"]]

    def reference(self, task: TaskRef) -> str | None:
        answer = self._entry(task).get("answer")
        return None if answer is None else str(answer)

    def prompt(self, task: TaskRef) -> str | None:
        return self._entry(task).get("question")

    def score(self, task: TaskRef, completion: str) -> float:
        from reasoning_gym.utils import extract_answer

        return self.dataset.score_answer(
            extract_answer(completion, tag_name=self.tag), self._entry(task)
        )

    def describe(self) -> dict[str, Any]:
        return {**super().describe(), "dataset": type(self.dataset).__name__, "tag": self.tag}
