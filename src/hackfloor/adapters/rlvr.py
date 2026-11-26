"""Adapter for plain reward functions (RLVR style): ``reward(completion, answer) -> float``.

Supported call conventions (``flavor``):

* ``plain``: ``fn(completion, answer)``
* ``verl``:  ``fn(data_source, solution_str, ground_truth, extra_info)``
* ``trl``:   ``fn(prompts=[...], completions=[...], **dataset_columns) -> list[float]``

``auto`` picks a flavor from the function's parameter names.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import math
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hackfloor.core import Action, Attempt, Capability, TaskRef

FLAVORS = ("auto", "plain", "verl", "trl")


def load_callable(spec: str, base_dir: Path | None = None) -> Callable[..., Any]:
    """Load ``path/to/file.py:fn`` or ``package.module:fn``."""
    if ":" not in spec:
        raise ValueError(f"expected 'file.py:function' or 'module:function', got {spec!r}")
    target, _, attr = spec.rpartition(":")
    path = Path(target)
    if base_dir is not None and not path.is_absolute():
        path = base_dir / path
    if target.endswith(".py") or path.exists():
        if not path.exists():
            raise FileNotFoundError(path)
        mod_name = f"hackfloor_subject_{abs(hash(str(path.resolve())))}"
        module_spec = importlib.util.spec_from_file_location(mod_name, path)
        if module_spec is None or module_spec.loader is None:
            raise ImportError(f"cannot import {path}")
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[mod_name] = module
        module_spec.loader.exec_module(module)
    else:
        module = importlib.import_module(target)
    fn = getattr(module, attr, None)
    if not callable(fn):
        raise AttributeError(f"{spec!r} is not a callable")
    return fn


def detect_flavor(fn: Callable[..., Any]) -> str:
    try:
        params = set(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        return "plain"
    if {"solution_str", "ground_truth"} <= params:
        return "verl"
    if "completions" in params:
        return "trl"
    return "plain"


def answer_in_text(answer: str, text: str | None) -> bool | None:
    if text is None or not answer.strip():
        return None
    pattern = r"(?<![\w.])" + re.escape(answer.strip()) + r"(?!\w|\.\d)"
    return re.search(pattern, text) is not None


def _lookup(row: dict[str, Any], key: str) -> Any:
    value: Any = row
    for part in key.split("."):
        value = value[part]
    return value


class RewardFunctionSubject:
    """A reward function plus a dataset of (prompt, answer) rows."""

    framework = "rlvr"

    def __init__(
        self,
        fn: Callable[..., Any],
        rows: list[dict[str, Any]],
        *,
        name: str = "reward_function",
        flavor: str = "auto",
        answer_key: str = "answer",
        prompt_key: str = "prompt",
        gold_template: str = "{answer}",
        reward_min: float = 0.0,
        reward_max: float = 1.0,
        source: str = "",
    ) -> None:
        if flavor not in FLAVORS:
            raise ValueError(f"flavor must be one of {FLAVORS}")
        if not rows:
            raise ValueError("the dataset is empty")
        self.fn = fn
        self.rows = rows
        self.name = name
        self.flavor = detect_flavor(fn) if flavor == "auto" else flavor
        self.answer_key = answer_key
        self.prompt_key = prompt_key
        self.gold_template = gold_template
        self.reward_min = reward_min
        self.reward_max = reward_max
        self.source = source

    @classmethod
    def from_paths(
        cls,
        reward: str,
        data: str | Path,
        *,
        base_dir: Path | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> RewardFunctionSubject:
        fn = load_callable(reward, base_dir)
        data_path = Path(data)
        if base_dir is not None and not data_path.is_absolute():
            data_path = base_dir / data_path
        rows = [
            json.loads(line)
            for line in data_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if limit is not None:
            rows = rows[:limit]
        kwargs.setdefault("name", reward)
        kwargs.setdefault("source", str(data_path))
        return cls(fn, rows, **kwargs)

    def capabilities(self) -> set[Capability]:
        return {Capability.COMPLETION}

    def tasks(self) -> list[TaskRef]:
        return [
            TaskRef(id=str(row.get("id", i)), meta={"index": i}) for i, row in enumerate(self.rows)
        ]

    def _row(self, task: TaskRef) -> dict[str, Any]:
        return self.rows[task.meta["index"]]

    def gold(self, task: TaskRef) -> Action:
        answer = str(_lookup(self._row(task), self.answer_key))
        return self.gold_template.replace("{answer}", answer)

    def null(self, task: TaskRef) -> Action:
        return ""

    def observation(self, task: TaskRef) -> str | None:
        prompt = self._row(task).get(self.prompt_key)
        if prompt is None:
            return None
        return prompt if isinstance(prompt, str) else json.dumps(prompt)

    def answer_visible(self, task: TaskRef) -> bool | None:
        """Whether the reference answer appears, as a whole token, in the prompt."""
        return answer_in_text(
            str(_lookup(self._row(task), self.answer_key)), self.observation(task)
        )

    def _call(self, row: dict[str, Any], completion: str) -> Any:
        answer = _lookup(row, self.answer_key)
        if self.flavor == "plain":
            return self.fn(completion, answer)
        if self.flavor == "verl":
            return self.fn(
                row.get("data_source", "hackfloor"),
                completion,
                answer,
                row.get("extra_info", {}),
            )
        columns = {k: [v] for k, v in row.items() if k not in ("prompts", "completions")}
        prompt = row.get(self.prompt_key, "")
        result = self.fn(prompts=[prompt], completions=[completion], **columns)
        return result[0]

    def grade(self, task: TaskRef, action: Action) -> Attempt:
        if not isinstance(action, str):
            raise TypeError("reward-function subjects grade completion strings only")
        try:
            raw = self._call(self._row(task), action)
            if isinstance(raw, dict):  # verl allows {"score": ...}
                raw = raw.get("score", raw.get("reward"))
            reward = float(raw)
        except Exception as exc:
            return Attempt(reward=float("nan"), error=f"{type(exc).__name__}: {exc}")
        if not math.isfinite(reward):
            return Attempt(reward=reward, error="non-finite reward")
        return Attempt(reward=reward)

    def describe(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "name": self.name,
            "flavor": self.flavor,
            "data": self.source,
            "n_rows": len(self.rows),
            "gold_template": self.gold_template,
            "reward_range": [self.reward_min, self.reward_max],
        }
