"""Adapter for file-based agent tasks (a Harbor-like layout), run in a local temp sandbox.

A task directory holds a ``hackfloor.toml`` that says where the agent's workspace is, where
the reference solution is, how to run the verifier and where it writes the reward::

    [task]
    environment = "environment"      # copied to a fresh sandbox root for every attempt
    workspace = "workspace"          # the directory the agent edits, relative to the root
    solution = "solution"            # overlaid onto the workspace for the gold run
    entry_file = "solution.py"       # optional: Python file the agent implements
    entry_functions = ["add"]        # optional: functions it must define
    visible_tests = ["tests/*.py"]   # optional: tests inside the agent's workspace

    [verifier]
    command = ["{python}", "{task}/grader/grade.py"]
    cwd = "{workspace}"
    reward = "file"                  # "file" or "exit_code"
    reward_file = "logs/reward.txt"  # relative to the sandbox root
    reward_file_agent_writable = true
    timeout = 60

v0.1 runs the verifier as a local subprocess. It is a probe harness, not a security
boundary: only scan environments you trust to run on this machine. Container isolation is
on the roadmap.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from hackfloor.core import Action, Attempt, Capability, TaskRef, Workspace

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

CONFIG_NAME = "hackfloor.toml"


def read_config(task_dir: Path) -> dict[str, Any]:
    with (task_dir / CONFIG_NAME).open("rb") as fh:
        return tomllib.load(fh)


class _TaskSpec:
    def __init__(self, task_dir: Path) -> None:
        cfg = read_config(task_dir)
        task = cfg.get("task", {})
        verifier = cfg.get("verifier", {})
        reward = cfg.get("reward", {})
        self.dir = task_dir.resolve()
        self.id = cfg.get("subject", {}).get("name", task_dir.name)
        self.environment = self.dir / task.get("environment", "environment")
        self.workspace = task.get("workspace", "workspace")
        self.solution = self.dir / task.get("solution", "solution")
        self.entry_file = task.get("entry_file")
        self.entry_functions = tuple(task.get("entry_functions", ()))
        self.visible_tests = tuple(task.get("visible_tests", ()))
        self.setup = list(task.get("setup", []))
        self.setup_timeout = float(task.get("setup_timeout", 60))
        instruction = self.dir / task.get("instruction", "instruction.md")
        self.instruction = (
            instruction.read_text(encoding="utf-8") if instruction.is_file() else None
        )
        self.command = list(verifier.get("command", []))
        self.cwd = verifier.get("cwd", "{workspace}")
        self.reward_mode = verifier.get("reward", "file")
        self.reward_file = verifier.get("reward_file")
        self.reward_file_writable = bool(verifier.get("reward_file_agent_writable", True))
        self.missing_reward = verifier.get("missing_reward")
        self.timeout = float(verifier.get("timeout", 60))
        self.reward_min = float(reward.get("min", 0.0))
        self.reward_max = float(reward.get("max", 1.0))
        if not self.command:
            raise ValueError(f"{task_dir / CONFIG_NAME}: [verifier] command is required")
        if self.reward_mode not in ("file", "exit_code"):
            raise ValueError("[verifier] reward must be 'file' or 'exit_code'")
        if self.reward_mode == "file" and not self.reward_file:
            raise ValueError("[verifier] reward = 'file' needs reward_file")
        if not self.environment.is_dir():
            raise FileNotFoundError(self.environment)


def _fill(text: str, spec: _TaskSpec, root: Path, workspace: Path, logs: Path) -> str:
    subs = {
        "{python}": sys.executable,
        "{task}": str(spec.dir),
        "{sandbox}": str(root),
        "{workspace}": str(workspace),
        "{logs}": str(logs),
    }
    for key, value in subs.items():
        text = text.replace(key, value)
    return text


def _env(spec: _TaskSpec, root: Path, workspace: Path, logs: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
    env.update(
        HACKFLOOR_SANDBOX=str(root),
        HACKFLOOR_WORKSPACE=str(workspace),
        HACKFLOOR_LOGS=str(logs),
        HACKFLOOR_TASK=str(spec.dir),
        PYTHONDONTWRITEBYTECODE="1",
    )
    return env


def _overlay(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


class TaskDirSubject:
    """One or more task directories graded by their own verifier command."""

    framework = "task"

    def __init__(self, task_dirs: list[Path], *, name: str | None = None) -> None:
        if not task_dirs:
            raise ValueError("no task directories given")
        self.specs = [_TaskSpec(Path(d)) for d in task_dirs]
        self.name = name or (self.specs[0].id if len(self.specs) == 1 else "task-suite")
        mins = {s.reward_min for s in self.specs}
        maxs = {s.reward_max for s in self.specs}
        if len(mins) != 1 or len(maxs) != 1:
            raise ValueError("all tasks in a suite must share one reward range")
        self.reward_min = mins.pop()
        self.reward_max = maxs.pop()

    def _spec(self, task: TaskRef) -> _TaskSpec:
        return self.specs[task.meta["index"]]

    def capabilities(self) -> set[Capability]:
        caps = {Capability.WORKSPACE}
        if all(s.entry_file and s.entry_functions for s in self.specs):
            caps.add(Capability.PYTHON_ENTRY)
        if all(s.visible_tests for s in self.specs):
            caps.add(Capability.VISIBLE_TESTS)
        if all(s.reward_mode == "file" and s.reward_file_writable for s in self.specs):
            caps.add(Capability.REWARD_FILE_WRITABLE)
        return caps

    def tasks(self) -> list[TaskRef]:
        return [TaskRef(id=s.id, meta={"index": i}) for i, s in enumerate(self.specs)]

    def gold(self, task: TaskRef) -> Action:
        solution = self._spec(task).solution

        def apply_solution(ws: Workspace) -> None:
            _overlay(solution, ws.path)

        return apply_solution

    def null(self, task: TaskRef) -> Action:
        def noop(ws: Workspace) -> None:
            return None

        return noop

    def observation(self, task: TaskRef) -> str | None:
        return self._spec(task).instruction

    @contextlib.contextmanager
    def sandbox_preview(self, task: TaskRef) -> Iterator[Workspace]:
        """A fresh, set-up sandbox that probes may inspect before choosing variants."""
        with tempfile.TemporaryDirectory(prefix="hackfloor-") as tmp:
            yield self._materialize(self._spec(task), Path(tmp))

    def _materialize(self, spec: _TaskSpec, tmp: Path) -> Workspace:
        root = tmp / "sandbox"
        shutil.copytree(spec.environment, root)
        workspace = root / spec.workspace
        workspace.mkdir(parents=True, exist_ok=True)
        logs = root / "logs"
        logs.mkdir(exist_ok=True)
        reward_path = root / spec.reward_file if spec.reward_file else None
        if spec.setup:
            proc = subprocess.run(
                [_fill(part, spec, root, workspace, logs) for part in spec.setup],
                cwd=workspace,
                env=_env(spec, root, workspace, logs),
                capture_output=True,
                text=True,
                timeout=spec.setup_timeout,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"task setup failed: {(proc.stdout + proc.stderr)[-500:]}")
        return Workspace(
            root,
            workspace,
            logs,
            entry_file=spec.entry_file,
            entry_functions=spec.entry_functions,
            visible_tests=spec.visible_tests,
            reward_file=reward_path,
            reward_min=spec.reward_min,
            reward_max=spec.reward_max,
        )

    def grade(self, task: TaskRef, action: Action) -> Attempt:
        if isinstance(action, str):
            raise TypeError("task subjects grade workspace actions, not completion strings")
        spec = self._spec(task)
        with tempfile.TemporaryDirectory(prefix="hackfloor-") as tmp:
            try:
                ws = self._materialize(spec, Path(tmp))
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                return Attempt(reward=float("nan"), error=str(exc))
            try:
                action(ws)
            except Exception as exc:
                return Attempt(reward=float("nan"), error=f"action failed: {exc}")
            return self._run_verifier(spec, ws.root, ws.path, ws.logs, ws.reward_file)

    def _run_verifier(
        self,
        spec: _TaskSpec,
        root: Path,
        workspace: Path,
        logs: Path,
        reward_path: Path | None,
    ) -> Attempt:
        env = _env(spec, root, workspace, logs)

        def fill(text: str) -> str:
            return _fill(text, spec, root, workspace, logs)

        try:
            proc = subprocess.run(
                [fill(part) for part in spec.command],
                cwd=fill(spec.cwd),
                env=env,
                capture_output=True,
                text=True,
                timeout=spec.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return Attempt(
                reward=spec.reward_min, detail=f"verifier timed out after {spec.timeout}s"
            )
        tail = (proc.stdout + proc.stderr)[-1500:]
        if spec.reward_mode == "exit_code":
            reward = spec.reward_max if proc.returncode == 0 else spec.reward_min
            return Attempt(reward=reward, detail=f"exit={proc.returncode}\n{tail}")
        assert reward_path is not None
        if not reward_path.exists():
            if spec.missing_reward is None:
                return Attempt(reward=float("nan"), error="verifier wrote no reward file")
            return Attempt(reward=float(spec.missing_reward), detail=f"no reward file\n{tail}")
        text = reward_path.read_text(encoding="utf-8").strip()
        try:
            if reward_path.suffix == ".json":
                data = json.loads(text)
                value = data.get("reward", data) if isinstance(data, dict) else data
                reward = float(value)
            else:
                reward = float(text)
        except (ValueError, TypeError) as exc:
            return Attempt(reward=float("nan"), error=f"unreadable reward file: {exc}")
        return Attempt(reward=reward, detail=f"exit={proc.returncode}\n{tail}")

    def describe(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "name": self.name,
            "tasks": [str(s.dir) for s in self.specs],
            "reward_range": [self.reward_min, self.reward_max],
            "isolation": "local temp-dir sandbox (no container)",
        }
