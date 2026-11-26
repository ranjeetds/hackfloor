"""The integrity card: a JSON record of one scan that anyone can re-check."""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

from hackfloor import stats
from hackfloor.scan import NOTHING_TO_TRY, ProbeResult, ScanResult

CARD_VERSION = "0.1"

#: Check ids follow OpenEnv's RFC 008 validation code (openenv/OpenEnv, v0.14). These are the
#: reward-integrity and containment criteria hackfloor does not measure yet. They are
#: listed so a card never implies coverage it does not have.
NOT_YET_MEASURED = {
    "semantic.canary_floor": "export of probes as OpenEnv canaries is planned",
    "runtime.network_policy": "needs container isolation (planned for v0.3)",
    "runtime.host_containment": "needs container isolation (planned for v0.3)",
    "runtime.resource_bounds": "needs container isolation (planned for v0.3)",
    "runtime.episode_isolation": "needs multi-episode runs (planned)",
}


def _r(x: float | None, nd: int = 4) -> float | None:
    return None if x is None else round(float(x), nd)


def _p(x: float | None) -> float | None:
    return None if x is None else float(f"{x:.3g}")


def _probe_entry(r: ProbeResult) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": r.probe.id,
        "family": r.probe.family,
        "title": r.probe.title,
        "maps_to": r.probe.rfc008,
        "status": r.status,
        "severity": r.severity,
    }
    if r.skipped_same_as_reference:
        entry["skipped_same_as_reference"] = r.skipped_same_as_reference
    if r.status in ("not_applicable", "error"):
        entry["message"] = r.message
        return entry
    lo, hi = r.hack_pass_ci
    entry.update(
        {
            "n_tasks": r.n,
            "floor_gap": {
                "mean": _r(r.delta_mean),
                "ci95": [_r(r.delta_ci[0]), _r(r.delta_ci[1])],
            },
            "hack_pass": {"k": r.hack_passes, "n": r.n, "ci95": [_r(lo), _r(hi)]},
            "pairs": {"wins": r.wins, "losses": r.losses, "ties": r.n - r.wins - r.losses},
            "decision": {
                "basis": r.basis,
                "p_value": _p(r.p_value),
                "p_holm": _p(r.p_adjusted),
                "replays_consistent": r.consistent,
            },
        }
    )
    ex = r.example()
    if ex is not None and r.status in ("finding", "info", "flaky"):
        entry["evidence"] = {
            "task": ex.task_id,
            "variant": ex.variant,
            "exploit_reward": _r(ex.exploit),
            "control_reward": _r(ex.control),
            "gold_reward": _r(ex.gold),
        }
    if r.message:
        entry["message"] = r.message
    return entry


def _check(status: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, **extra}


def _gameability(result: ScanResult) -> dict[str, Any]:
    labels = [solved for solved, _ in result.samples]
    values = [reward for _, reward in result.samples]
    r = stats.point_biserial(labels, values)
    auc = stats.auroc(labels, values)
    bound = result.config.gameability_bound
    scope = "scripted policies only: reference = solved; null, probes, controls = not solved"
    if r is None:
        return _check("SKIP", reason="reward or success is constant across attempts", scope=scope)
    return _check(
        "PASS" if r >= bound else "FAIL",
        correlation=_r(r),
        auroc=_r(auc),
        declared_bound=bound,
        n_attempts=len(values),
        scope=scope,
    )


def _leakage(result: ScanResult) -> dict[str, Any]:
    leak_probes = [p for p in result.probes if p.probe.rfc008 == "semantic.no_solution_leakage"]
    ran = [p for p in leak_probes if p.status not in ("not_applicable", "error")]
    # A leak probe that searched the sandbox and found nothing to copy is evidence too.
    searched = [p for p in leak_probes if p.message == NOTHING_TO_TRY]
    found = [p.probe.id for p in ran if p.status == "finding"]
    visible, checked = result.leaks
    if not ran and not searched and not checked:
        return _check("NOT_MEASURED", reason="no leak probe applies and no observation to check")
    status = "FAIL" if found or visible else "PASS"
    return _check(
        status,
        probes_run=[p.probe.id for p in ran],
        searched_nothing_found=[p.probe.id for p in searched],
        findings=found,
        answer_visible_in_observation={"tasks": visible, "checked": checked},
    )


def build_card(result: ScanResult, *, command: str = "") -> dict[str, Any]:
    from hackfloor import __version__

    cal = result.calibration
    # Every probe is a non-solving policy, so all of them form the adversarial panel except the
    # containment probes, which are reported under runtime.oracle_containment.
    floor_probes = [p for p in result.probes if not p.probe.rfc008.startswith("runtime.")]
    floor_findings = [p for p in floor_probes if p.status == "finding"]
    floor_ran = [p for p in floor_probes if p.status not in ("not_applicable", "error")]
    clean_n = sum(p.n for p in floor_ran)

    lo, hi = result.reward_range
    width = hi - lo
    margin = result.config.delta
    gold_min = min(cal.gold.values())
    null_max = max(cal.null.values())
    checks: dict[str, Any] = {
        "hackfloor.calibration": _check(
            cal.sanity,
            gold_mean=_r(cal.gold_mean),
            null_mean=_r(cal.null_mean),
            reasons=cal.reasons,
        ),
        "semantic.oracle_max": _check(
            "PASS" if gold_min >= hi - 1e-9 else "FAIL",
            lowest_reference_reward=_r(gold_min),
            declared_max=hi,
            oracle_tolerance=0.0,
        ),
        "semantic.floor_gap": _check(
            "PASS"
            if hi - null_max >= margin * width - 1e-9
            and gold_min - null_max >= margin * width - 1e-9
            else "FAIL",
            measured_floor=_r(null_max),
            lowest_reference_reward=_r(gold_min),
            floor_margin=margin,
        ),
        "statistical.adversarial_floor": _check(
            "FAIL" if floor_findings else ("PASS" if floor_ran else "SKIP"),
            probes_run=[p.probe.id for p in floor_ran],
            findings=[p.probe.id for p in floor_findings],
            partial_credit=[p.probe.id for p in floor_ran if p.status == "info"],
            **(
                {}
                if floor_findings or not clean_n
                else {"hack_pass_upper95_per_probe_task": _r(1 - 0.05 ** (1 / max(1, clean_n)))}
            ),
        ),
        "statistical.gameability_gap": _gameability(result),
        "semantic.no_solution_leakage": _leakage(result),
        "runtime.reward_well_formed": _check(
            "FAIL" if result.errors else "PASS",
            errors=result.errors[:20],
            n_errors=len(result.errors),
        ),
    }
    containment = [p for p in result.probes if p.probe.rfc008 == "runtime.oracle_containment"]
    for p in containment:
        status = {"finding": "FAIL", "resisted": "PASS"}.get(p.status, "SKIP")
        checks["runtime.oracle_containment"] = _check(
            status, scope="reward-file write only (partial)", probe=p.probe.id
        )
    for key, why in NOT_YET_MEASURED.items():
        checks.setdefault(key, _check("NOT_MEASURED", reason=why))

    probe_ids = sorted(p.probe.id for p in result.probes)
    card: dict[str, Any] = {
        "card_version": CARD_VERSION,
        "tool": {"name": "hackfloor", "version": __version__},
        "created_at": datetime.fromtimestamp(result.started_at, tz=timezone.utc).isoformat(
            timespec="seconds"
        ),
        "subject": result.subject,
        "verdict": result.verdict,
        "level": result.level,
        "level_scope": "hackfloor 0.2 issues levels 0 and 1 only",
        "summary": {
            "tasks": len(result.tasks),
            "probes_run": sum(p.status not in ("not_applicable", "error") for p in result.probes),
            "findings": len(result.findings),
            "partial_credit": len(result.partial_credit),
            "worst_severity": result.worst_severity,
            "seconds": round(result.seconds, 2),
        },
        "calibration": {
            "reward_range": list(result.reward_range),
            "gold_mean": _r(cal.gold_mean),
            "null_mean": _r(cal.null_mean),
            "replays_consistent": cal.consistent,
        },
        "probes": [_probe_entry(p) for p in result.probes],
        "checks": checks,
        "method": {
            "replays": result.config.replays,
            "alpha": result.config.alpha,
            "min_floor_gap": result.config.delta,
            "partial_credit_bound": result.config.partial_credit,
            "min_tasks_for_sign_test": result.config.min_tasks_for_test,
            "seed": result.config.seed,
            "probe_set": hashlib.sha256(",".join(probe_ids).encode()).hexdigest()[:12],
        },
        "environment": {"python": platform.python_version(), "platform": platform.system()},
        "reproduce": command,
    }
    return card


def write_card(card: dict[str, Any], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    return out


def card_schema() -> dict[str, Any]:
    text = resources.files("hackfloor").joinpath("schema/card-0.1.schema.json").read_text("utf-8")
    return json.loads(text)
