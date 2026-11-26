"""Core data types shared by adapters, probes and the scan engine."""

from __future__ import annotations

import math
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class Capability(str, Enum):
    """What a subject lets a probe do. Probes declare the capabilities they need."""

    COMPLETION = "completion"  # the policy's action is a single completion string
    WORKSPACE = "workspace"  # the policy edits files in a sandboxed workspace
    PYTHON_ENTRY = "python_entry"  # the task names a Python file and functions to implement
    VISIBLE_TESTS = "visible_tests"  # tests the grader trusts are inside the agent's workspace
    REWARD_FILE_WRITABLE = "reward_file_writable"  # the reward file is reachable by the agent


@dataclass(frozen=True)
class TaskRef:
    """One task (a data row, or one task directory) a subject can grade."""

    id: str
    meta: dict[str, Any] = field(default_factory=dict)


class Workspace:
    """A fresh sandbox copy of a task environment that a workspace probe may modify."""

    def __init__(
        self,
        root: Path,
        workspace: Path,
        logs: Path,
        *,
        entry_file: str | None = None,
        entry_functions: tuple[str, ...] = (),
        visible_tests: tuple[str, ...] = (),
        reward_file: Path | None = None,
        reward_min: float = 0.0,
        reward_max: float = 1.0,
    ) -> None:
        self.root = root
        self.path = workspace
        self.logs = logs
        self.entry_file = entry_file
        self.entry_functions = entry_functions
        self.visible_test_globs = visible_tests
        self.reward_file = reward_file
        self.reward_min = reward_min
        self.reward_max = reward_max

    def write(self, rel: str, text: str) -> Path:
        """Write a file relative to the workspace (the directory the agent edits)."""
        target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def read(self, rel: str) -> str:
        return (self.path / rel).read_text(encoding="utf-8")

    def delete(self, rel: str) -> None:
        target = self.path / rel
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

    def visible_tests(self) -> list[Path]:
        found: set[Path] = set()
        for pattern in self.visible_test_globs:
            found.update(p for p in self.path.glob(pattern) if p.is_file())
        return sorted(found)

    def write_reward_file(self, value: float) -> None:
        if self.reward_file is None:
            raise RuntimeError("this task declares no reward file")
        self.reward_file.parent.mkdir(parents=True, exist_ok=True)
        self.reward_file.write_text(f"{value}\n", encoding="utf-8")


#: A policy action: a completion string, or a function that edits a Workspace.
Action = str | Callable[[Workspace], None]


@dataclass
class Attempt:
    """The graded outcome of one action on one task."""

    reward: float
    error: str | None = None
    detail: str = ""

    @property
    def well_formed(self) -> bool:
        return self.error is None and math.isfinite(self.reward)


class Subject(Protocol):
    """An environment hackfloor can probe. Adapters implement this protocol."""

    framework: str
    name: str
    reward_min: float
    reward_max: float

    def capabilities(self) -> set[Capability]: ...

    def tasks(self) -> list[TaskRef]: ...

    def gold(self, task: TaskRef) -> Action:
        """The reference solution for a task, as an action."""
        ...

    def null(self, task: TaskRef) -> Action:
        """The empty-trajectory policy: an empty completion, or an unchanged workspace."""
        ...

    def grade(self, task: TaskRef, action: Action) -> Attempt: ...

    def describe(self) -> dict[str, Any]: ...
