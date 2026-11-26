"""Adapter for Prime Intellect ``verifiers`` tasksets (v1 API, ``import verifiers.v1``).

Experimental. Each task is scored with the taskset's own ``Task.score(trace)`` on a
two-node trace (the prompt as a user message, the completion as the sampled assistant
reply), and the reward is ``trace.reward``, the weighted sum of the task's rewards.
Rewards that need a sandbox runtime are skipped by verifiers when no runtime is attached,
so this covers trace-only rewards; tasks graded inside a sandbox are out of scope here.

The gold completion is ``gold_template`` with the task data's ``answer`` field, so the
template must reproduce the format the rewards parse (for reverse-text,
``<reversed_text>{answer}</reversed_text>``).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from hackfloor.adapters.base import CompletionSubject
from hackfloor.core import TaskRef


def _vf() -> Any:
    try:
        import verifiers.v1 as vf
    except ImportError as exc:
        raise ImportError(
            "the verifiers adapter needs `pip install hackfloor[verifiers]` (Python 3.11+)"
        ) from exc
    return vf


class VerifiersSubject(CompletionSubject):
    framework = "verifiers"

    def __init__(
        self,
        tasks: Iterable[Any],
        *,
        name: str = "verifiers",
        gold_template: str = "{answer}",
        answer_field: str = "answer",
        reward_min: float = 0.0,
        reward_max: float = 1.0,
        limit: int | None = None,
    ) -> None:
        super().__init__(
            name=name, gold_template=gold_template, reward_min=reward_min, reward_max=reward_max
        )
        self._vf = _vf()
        loaded = []
        for task in tasks:  # a Taskset iterates its tasks with idx set
            if limit is not None and len(loaded) >= limit:
                break
            loaded.append(task)
        if not loaded:
            raise ValueError("the taskset yielded no tasks")
        self.vf_tasks = loaded
        self.answer_field = answer_field

    def tasks(self) -> list[TaskRef]:
        out = []
        for i, task in enumerate(self.vf_tasks):
            data = task.data
            ident = getattr(data, "id", None) or getattr(data, "name", None) or str(i)
            out.append(TaskRef(id=str(ident), meta={"index": i}))
        return out

    def _task(self, task: TaskRef) -> Any:
        return self.vf_tasks[task.meta["index"]]

    def reference(self, task: TaskRef) -> str | None:
        answer = getattr(self._task(task).data, self.answer_field, None)
        return None if answer is None else str(answer)

    def prompt(self, task: TaskRef) -> str | None:
        prompt = self._task(task).data.prompt
        if prompt is None or isinstance(prompt, str):
            return prompt
        parts = [m.content for m in prompt if isinstance(getattr(m, "content", None), str)]
        return "\n".join(parts)

    def _trace(self, vf_task: Any, completion: str) -> Any:
        from verifiers.v1.graph import MessageNode
        from verifiers.v1.types import AssistantMessage, UserMessage

        vf = self._vf
        prompt = vf_task.data.prompt
        messages = (
            [UserMessage(content=prompt or "")]
            if prompt is None or isinstance(prompt, str)
            else list(prompt)
        )
        nodes = []
        for i, message in enumerate(messages):
            nodes.append(MessageNode(parent=i - 1 if i else None, message=message, sampled=False))
        nodes.append(
            MessageNode(
                parent=len(messages) - 1,
                message=AssistantMessage(content=completion),
                sampled=True,
            )
        )
        return vf.Trace(
            agent=vf.AgentInfo(config=vf.AgentConfig()),
            task=vf.TraceTask(type=type(vf_task).__name__, data=vf_task.data),
            nodes=nodes,
        )

    def score(self, task: TaskRef, completion: str) -> float:
        vf_task = self._task(task)
        trace = self._trace(vf_task, completion)
        asyncio.run(vf_task.score(trace))
        return float(trace.reward)

    def describe(self) -> dict[str, Any]:
        return {**super().describe(), "experimental": True}
