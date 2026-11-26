"""Adapters turn an environment into a Subject that probes can be run against."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from hackfloor.adapters.rlvr import RewardFunctionSubject
from hackfloor.adapters.taskdir import CONFIG_NAME, TaskDirSubject, read_config
from hackfloor.core import Subject

__all__ = ["RewardFunctionSubject", "TaskDirSubject", "resolve_subject"]


def _rlvr_from_config(target: Path, cfg: dict[str, Any], **overrides: Any) -> Subject:
    sub = cfg.get("subject", {})
    reward = cfg.get("reward", {})
    kwargs: dict[str, Any] = {
        "flavor": overrides.get("flavor") or sub.get("flavor", "auto"),
        "gold_template": overrides.get("gold_template") or sub.get("gold_template", "{answer}"),
        "answer_key": sub.get("answer_key", "answer"),
        "prompt_key": sub.get("prompt_key", "prompt"),
        "reward_min": float(reward.get("min", 0.0)),
        "reward_max": float(reward.get("max", 1.0)),
        "name": sub.get("name", target.name),
    }
    return RewardFunctionSubject.from_paths(
        sub["reward"],
        overrides.get("data") or sub["data"],
        base_dir=target,
        limit=overrides.get("limit"),
        **kwargs,
    )


def resolve_subject(
    target: str,
    *,
    data: str | None = None,
    flavor: str | None = None,
    gold_template: str | None = None,
    limit: int | None = None,
) -> Subject:
    """Turn a CLI target into a Subject.

    * ``file.py:fn`` or ``module:fn`` with ``data``: a reward function.
    * a directory with ``hackfloor.toml``: an RLVR subject or a single task.
    * a directory whose subdirectories hold task ``hackfloor.toml`` files: a task suite.
    """
    path = Path(target)
    if path.is_dir():
        config = path / CONFIG_NAME
        if config.exists():
            cfg = read_config(path)
            kind = cfg.get("subject", {}).get("kind", "task")
            if kind == "rlvr":
                return _rlvr_from_config(
                    path, cfg, data=data, flavor=flavor, gold_template=gold_template, limit=limit
                )
            return TaskDirSubject([path])
        children = sorted(p for p in path.iterdir() if (p / CONFIG_NAME).exists())
        task_dirs = [
            p for p in children if read_config(p).get("subject", {}).get("kind", "task") == "task"
        ]
        if task_dirs:
            return TaskDirSubject(task_dirs[:limit] if limit else task_dirs, name=path.name)
        raise FileNotFoundError(f"{path} has no {CONFIG_NAME} and no task subdirectories")
    if ":" in target:
        if not data:
            raise ValueError("a reward-function target needs --data rows.jsonl")
        if str(Path.cwd()) not in sys.path:
            sys.path.insert(0, str(Path.cwd()))
        return RewardFunctionSubject.from_paths(
            target,
            data,
            flavor=flavor or "auto",
            gold_template=gold_template or "{answer}",
            limit=limit,
        )
    raise FileNotFoundError(f"cannot resolve scan target {target!r}")
