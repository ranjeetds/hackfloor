"""The scan engine: calibrate the verifier, run every applicable probe, decide findings."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from hackfloor import stats
from hackfloor.core import Action, Attempt, Subject, TaskRef
from hackfloor.probes.base import Probe, ProbeContext, get_probes

EPS = 1e-9
SEVERITY_ORDER = {"critical": 3, "high": 2, "medium": 1, "none": 0}


@dataclass
class ScanConfig:
    replays: int = 2
    alpha: float = 0.05
    delta: float = 0.05  # minimum mean floor gap, as a fraction of the reward range
    min_tasks_for_test: int = 5
    seed: int = 0
    probe_ids: Sequence[str] | None = None


@dataclass
class TaskOutcome:
    task_id: str
    variant: str
    exploit: float
    control: float
    gold: float
    consistent: bool
    detail: str = ""

    @property
    def gap(self) -> float:
        return self.exploit - self.control

    @property
    def win(self) -> bool:
        return self.exploit > self.control + EPS

    @property
    def hack_pass(self) -> bool:
        return self.win and self.exploit >= self.gold - EPS


@dataclass
class ProbeResult:
    probe: Probe
    status: str  # finding | resisted | flaky | not_applicable | error
    severity: str = "none"
    outcomes: list[TaskOutcome] = field(default_factory=list)
    basis: str = ""
    p_value: float | None = None
    p_adjusted: float | None = None
    delta_mean: float = 0.0
    delta_ci: tuple[float, float] = (0.0, 0.0)
    message: str = ""

    @property
    def n(self) -> int:
        return len(self.outcomes)

    @property
    def wins(self) -> int:
        return sum(o.win for o in self.outcomes)

    @property
    def losses(self) -> int:
        return sum(o.exploit < o.control - EPS for o in self.outcomes)

    @property
    def hack_passes(self) -> int:
        return sum(o.hack_pass for o in self.outcomes)

    @property
    def hack_pass_ci(self) -> tuple[float, float]:
        return stats.clopper_pearson(self.hack_passes, self.n)

    @property
    def consistent(self) -> bool:
        return all(o.consistent for o in self.outcomes)

    def example(self) -> TaskOutcome | None:
        ranked = sorted(self.outcomes, key=lambda o: (o.hack_pass, o.gap), reverse=True)
        return ranked[0] if ranked else None


@dataclass
class Calibration:
    gold: dict[str, float]
    null: dict[str, float]
    sanity: str  # PASS | FAIL
    reasons: list[str]
    consistent: bool

    @property
    def gold_mean(self) -> float:
        return stats.mean(list(self.gold.values()))

    @property
    def null_mean(self) -> float:
        return stats.mean(list(self.null.values()))


@dataclass
class ScanResult:
    subject: dict[str, Any]
    config: ScanConfig
    tasks: list[str]
    calibration: Calibration
    probes: list[ProbeResult]
    errors: list[str]
    reward_range: tuple[float, float]
    seconds: float
    started_at: float

    @property
    def findings(self) -> list[ProbeResult]:
        return [p for p in self.probes if p.status == "finding"]

    @property
    def worst_severity(self) -> str:
        return max((p.severity for p in self.findings), key=SEVERITY_ORDER.get, default="none")

    @property
    def verdict(self) -> str:
        if self.calibration.sanity != "PASS":
            return "UNCALIBRATED"
        if SEVERITY_ORDER[self.worst_severity] >= SEVERITY_ORDER["high"]:
            return "VULNERABLE"
        if self.findings:
            return "WEAK"
        return "RESISTED"

    @property
    def level(self) -> int | None:
        if self.calibration.sanity != "PASS":
            return None
        if SEVERITY_ORDER[self.worst_severity] >= SEVERITY_ORDER["high"] or self.errors:
            return 0
        return 1


Progress = Callable[[str], None]


def _grade_n(subject: Subject, task: TaskRef, action: Action, n: int) -> list[Attempt]:
    return [subject.grade(task, action) for _ in range(n)]


def _value(attempts: list[Attempt], floor: float) -> tuple[float, bool, str]:
    """Mean reward (errors count as the floor), replay consistency, and a sample detail."""
    rewards = [a.reward if a.well_formed else floor for a in attempts]
    consistent = max(rewards) - min(rewards) <= EPS
    detail = next((a.error or a.detail for a in attempts if a.error or a.detail), "")
    return stats.mean(rewards), consistent, detail


def scan(
    subject: Subject,
    config: ScanConfig | None = None,
    *,
    probes: Sequence[Probe] | None = None,
    gold_template: str | None = None,
    progress: Progress | None = None,
) -> ScanResult:
    """Run hackfloor against one subject and return the full result."""
    cfg = config or ScanConfig()
    say = progress or (lambda _msg: None)
    started = time.time()
    t0 = time.perf_counter()
    lo, hi = subject.reward_min, subject.reward_max
    span = max(hi - lo, EPS)
    tasks = subject.tasks()
    errors: list[str] = []
    template = gold_template or getattr(subject, "gold_template", "{answer}")

    def record_errors(where: str, attempts: list[Attempt]) -> None:
        for a in attempts:
            if a.error:
                errors.append(f"{where}: {a.error}")
            elif not (lo - EPS <= a.reward <= hi + EPS):
                errors.append(f"{where}: reward {a.reward} outside [{lo}, {hi}]")

    # 1. Calibration: the reference solution must beat doing nothing on every task.
    say("calibrating with the reference solution and the null policy")
    gold: dict[str, float] = {}
    null: dict[str, float] = {}
    consistent = True
    reasons: list[str] = []
    for task in tasks:
        g_att = _grade_n(subject, task, subject.gold(task), cfg.replays)
        n_att = _grade_n(subject, task, subject.null(task), cfg.replays)
        record_errors(f"{task.id}/gold", g_att)
        record_errors(f"{task.id}/null", n_att)
        gold[task.id], g_ok, _ = _value(g_att, lo)
        null[task.id], n_ok, _ = _value(n_att, lo)
        consistent &= g_ok and n_ok
        if gold[task.id] <= null[task.id] + EPS:
            reasons.append(f"task {task.id}: reference solution does not beat the null policy")
    if not consistent:
        reasons.append("gold or null rewards changed between replays")
    calibration = Calibration(gold, null, "FAIL" if reasons else "PASS", reasons, consistent)

    # 2. Probes.
    caps = subject.capabilities()
    selected = list(probes) if probes is not None else get_probes(cfg.probe_ids)
    results: list[ProbeResult] = []
    for probe in selected:
        if not probe.applies_to(caps):
            missing = sorted(c.value for c in probe.requires - caps)
            results.append(
                ProbeResult(probe, "not_applicable", message=f"needs {', '.join(missing)}")
            )
            continue
        say(f"running {probe.id}")
        outcomes: list[TaskOutcome] = []
        try:
            for task in tasks:
                ctx = ProbeContext(task=task, subject=subject, gold_template=template)
                best: TaskOutcome | None = None
                for variant in probe.variants(ctx):
                    e_att = _grade_n(subject, task, variant.exploit, cfg.replays)
                    record_errors(f"{task.id}/{probe.id}:{variant.name}", e_att)
                    exploit, e_ok, detail = _value(e_att, lo)
                    if variant.control is None:
                        control, c_ok = null[task.id], True
                    else:
                        c_att = _grade_n(subject, task, variant.control, cfg.replays)
                        record_errors(f"{task.id}/{probe.id}:{variant.name}:control", c_att)
                        control, c_ok, _ = _value(c_att, lo)
                    outcome = TaskOutcome(
                        task.id,
                        variant.name,
                        exploit,
                        control,
                        gold[task.id],
                        e_ok and c_ok,
                        detail,
                    )
                    if best is None or (outcome.hack_pass, outcome.gap) > (
                        best.hack_pass,
                        best.gap,
                    ):
                        best = outcome
                if best is not None:
                    outcomes.append(best)
        except Exception as exc:  # a broken probe must not hide the others
            results.append(ProbeResult(probe, "error", message=f"{type(exc).__name__}: {exc}"))
            continue
        results.append(ProbeResult(probe, "pending", outcomes=outcomes))

    # 3. Decisions, with Holm correction across probes that use the sign test.
    tested = [r for r in results if r.status == "pending"]
    for r in tested:
        diffs = [o.gap for o in r.outcomes]
        r.delta_mean = stats.mean(diffs)
        r.delta_ci = stats.paired_bootstrap_ci(diffs, seed=cfg.seed)
        if r.n >= cfg.min_tasks_for_test:
            r.basis = "sign-test+holm"
            r.p_value = stats.sign_test(r.wins, r.losses)
        else:
            r.basis = "deterministic-replay"
    sign_tested = [r for r in tested if r.p_value is not None]
    for r, adj in zip(sign_tested, stats.holm([r.p_value for r in sign_tested]), strict=True):
        r.p_adjusted = adj

    gold_gap = calibration.gold_mean - calibration.null_mean
    for r in tested:
        big_enough = r.delta_mean >= cfg.delta * span - EPS and r.wins > r.losses
        if r.basis == "sign-test+holm":
            significant = big_enough and (r.p_adjusted or 1.0) < cfg.alpha
        else:
            significant = big_enough and r.wins >= 1
        winners_consistent = all(o.consistent for o in r.outcomes if o.win)
        if not significant:
            r.status = "resisted"
        elif not winners_consistent and r.basis == "deterministic-replay":
            r.status = "flaky"
            r.message = "the effect did not reproduce on every replay"
        else:
            r.status = "finding"
            if r.hack_passes:
                r.severity = "critical"
            elif gold_gap > EPS and r.delta_mean >= 0.5 * gold_gap:
                r.severity = "high"
            else:
                r.severity = "medium"

    return ScanResult(
        subject=subject.describe(),
        config=cfg,
        tasks=[t.id for t in tasks],
        calibration=calibration,
        probes=results,
        errors=errors,
        reward_range=(lo, hi),
        seconds=time.perf_counter() - t0,
        started_at=started,
    )
