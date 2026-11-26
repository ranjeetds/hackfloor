"""Export an integrity card as OpenEnv RFC 008 ``CheckResult`` records.

The records follow ``$defs.CheckResult`` in OpenEnv's ``report-v2.schema.json``
(openenv/OpenEnv, v0.14): ``check_id``, a lowercase ``status`` (pass, fail, skip, error),
``measured``, ``evidence``, ``remediation`` and ``duration_s``. Severity is left to the
consuming policy, as the schema requires.

Only RFC 008 namespaces are exported (``semantic.*``, ``statistical.*``, ``runtime.*``).
hackfloor's own calibration check is folded into the evidence: an uncalibrated scan makes
every measured check ``skip``, because no floor can be trusted without it. Checks hackfloor
does not measure are exported as ``skip`` with the reason, never as ``pass``.

``statistical.adversarial_floor`` and ``statistical.gameability_gap`` sit in a lane RFC 008
reserves for operators; hackfloor is one way to produce them. All checks are derived from
the same set of attempts, so the scan's wall time is reported on
``statistical.adversarial_floor`` and the derived checks report 0.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RFC008_NAMESPACES = ("semantic.", "statistical.", "runtime.")

_STATUS = {"PASS": "pass", "FAIL": "fail", "SKIP": "skip", "NOT_MEASURED": "skip"}

_REMEDIATION = {
    "semantic.oracle_max": "Make the reference solution reach the declared maximum reward.",
    "semantic.floor_gap": "Make the empty trajectory score clearly below the reference.",
    "statistical.adversarial_floor": (
        "Fix the grader so each listed exploit scores at the floor; the card has a minimal "
        "reproduction per finding."
    ),
    "statistical.gameability_gap": (
        "Rewards should separate solved from unsolved attempts; see the probes that score "
        "unsolved attempts highly."
    ),
    "semantic.no_solution_leakage": (
        "Remove reference answers from what the agent can see or reach (prompt, workspace, "
        "git history)."
    ),
    "runtime.reward_well_formed": "Return a finite number in the declared range on every input.",
    "runtime.oracle_containment": "Keep the reward file out of the agent's reach.",
}

_SKIP_KEYS = ("status", "reason")


def _evidence(check_id: str, body: dict[str, Any], card: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if "reason" in body:
        lines.append(f"not measured: {body['reason']}")
    if check_id == "statistical.adversarial_floor":
        by_id = {p["id"]: p for p in card.get("probes", [])}
        for pid in body.get("findings", []):
            p = by_id.get(pid, {})
            lines.append(f"{pid} ({p.get('severity', '?')}): {p.get('title', '')}".rstrip(": "))
        if body.get("probes_run"):
            lines.append("probes run: " + ", ".join(body["probes_run"]))
    elif check_id == "semantic.no_solution_leakage":
        for pid in body.get("findings", []):
            lines.append(f"{pid} reached a reference solution")
        vis = body.get("answer_visible_in_observation") or {}
        if vis.get("tasks"):
            lines.append(f"reference answer visible in the prompt on {vis['tasks']} tasks")
    elif check_id == "runtime.reward_well_formed":
        lines.extend(str(e) for e in body.get("errors", [])[:5])
    version = card.get("tool", {}).get("version", "?")
    lines.append(f"hackfloor {version} card, verdict {card.get('verdict')}")
    return lines


def openenv_check_results(card: dict[str, Any]) -> list[dict[str, Any]]:
    """The card's RFC 008 checks as a list of OpenEnv ``CheckResult`` dicts."""
    calibrated = card.get("checks", {}).get("hackfloor.calibration", {}).get("status") == "PASS"
    seconds = float(card.get("summary", {}).get("seconds") or 0.0)
    out: list[dict[str, Any]] = []
    for check_id, body in card.get("checks", {}).items():
        if not check_id.startswith(RFC008_NAMESPACES):
            continue
        status = _STATUS.get(body.get("status", ""), "error")
        measured = {k: v for k, v in body.items() if k not in _SKIP_KEYS}
        evidence = _evidence(check_id, body, card)
        if not calibrated and status in ("pass", "fail"):
            status = "skip"
            evidence.insert(0, "uncalibrated: the reference does not separate from the floor")
        out.append(
            {
                "check_id": check_id,
                "status": status,
                "measured": measured,
                "evidence": evidence,
                "remediation": _REMEDIATION.get(check_id) if status == "fail" else None,
                "duration_s": seconds if check_id == "statistical.adversarial_floor" else 0.0,
            }
        )
    return out


def write_openenv_checks(card: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": "hackfloor", "checks": openenv_check_results(card)}
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target
