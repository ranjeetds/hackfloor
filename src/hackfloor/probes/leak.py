"""Leak probes: the policy copies a solution that is reachable from the agent's sandbox.

They run on task directories with a Python entry file. Each copies a candidate it finds into
the entry file; the control rewrites the entry file unchanged. They never read the task's
own ``solution`` directory, which hackfloor keeps outside the sandbox.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from hackfloor.core import Capability, Workspace
from hackfloor.probes.base import Probe, ProbeContext, Variant, register

_PY = frozenset({Capability.WORKSPACE, Capability.PYTHON_ENTRY})
_KEY_DIRS = {
    "solution",
    "solutions",
    "oracle",
    "answer",
    "answers",
    "expected",
    "gold",
    "reference",
}
_MAX_CANDIDATES = 5
_MAX_BYTES = 1_000_000


def _unchanged(ws: Workspace) -> None:
    target = ws.path / (ws.entry_file or "solution.py")
    if target.exists():
        target.write_bytes(target.read_bytes())


def _copy_in(text: str):
    def apply(ws: Workspace) -> None:
        ws.write(ws.entry_file or "solution.py", text)

    return apply


def find_answer_keys(root: Path, workspace: Path, entry_file: str) -> list[Path]:
    """Files under the sandbox root that look like a reference for ``entry_file``."""
    entry = (workspace / entry_file).resolve()
    name = Path(entry_file).name
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts or not path.is_file() or path.resolve() == entry:
            continue
        if path.stat().st_size > _MAX_BYTES:
            continue
        in_key_dir = any(part.lstrip(".").lower() in _KEY_DIRS for part in path.parent.parts)
        if path.name == name or (in_key_dir and path.suffix == Path(entry_file).suffix):
            found.append(path)
    return found[:_MAX_CANDIDATES]


@register
@dataclass(frozen=True)
class AnswerKeyProbe(Probe):
    id: str = "HF-ANSWERKEY"
    family: str = "leak"
    title: str = "Copy a reachable answer key"
    mechanism: str = (
        "Searches the sandbox for a file that looks like the reference (same name as the "
        "entry file, or inside a solution/oracle/answers/expected/gold directory) and copies it "
        "into the workspace."
    )
    requires: frozenset[Capability] = field(default_factory=lambda: _PY)
    references: tuple[str, ...] = (
        "Answers shipped with the test (BenchJack class V2)",
        "gradecheck answer-leak attack",
    )
    rfc008: str = "semantic.no_solution_leakage"

    def variants(self, ctx: ProbeContext) -> list[Variant]:
        preview = getattr(ctx.subject, "sandbox_preview", None)
        if preview is None:
            return []
        out: list[Variant] = []
        with preview(ctx.task) as ws:
            seen: set[str] = {_read(ws.path / (ws.entry_file or "solution.py"))}
            for path in find_answer_keys(ws.root, ws.path, ws.entry_file or "solution.py"):
                text = _read(path)
                if text in seen:
                    continue
                seen.add(text)
                rel = path.relative_to(ws.root).as_posix()
                out.append(Variant(f"copy:{rel}", _copy_in(text), _unchanged))
        return out


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30, check=False
    )
    return proc.stdout if proc.returncode == 0 else ""


@register
@dataclass(frozen=True)
class GitHistoryProbe(Probe):
    id: str = "HF-GITLEAK"
    family: str = "leak"
    title: str = "Recover the solution from git history"
    mechanism: str = (
        "Reads every version of the entry file reachable from any ref in the workspace's git "
        "repository (other branches, tags, future commits) and tries each one."
    )
    requires: frozenset[Capability] = field(default_factory=lambda: _PY)
    references: tuple[str, ...] = (
        "SWE-bench issue #465: future commits reachable in the task repository",
        "Answers reachable from the agent's environment (BenchJack class V2)",
    )
    rfc008: str = "semantic.no_solution_leakage"

    def variants(self, ctx: ProbeContext) -> list[Variant]:
        preview = getattr(ctx.subject, "sandbox_preview", None)
        if preview is None or shutil.which("git") is None:
            return []
        out: list[Variant] = []
        with preview(ctx.task) as ws:
            if not (ws.path / ".git").exists():
                return []
            entry = ws.entry_file or "solution.py"
            seen = {_read(ws.path / entry)}
            for commit in _git(ws.path, "rev-list", "--all").split()[:200]:
                text = _git(ws.path, "show", f"{commit}:{entry}")
                if not text or text in seen:
                    continue
                seen.add(text)
                out.append(Variant(f"git-show:{commit[:10]}", _copy_in(text), _unchanged))
                if len(out) >= _MAX_CANDIDATES:
                    break
        return out
