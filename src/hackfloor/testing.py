"""Assertions for using hackfloor inside a test suite.

>>> from hackfloor.testing import assert_resists
>>> card = assert_resists("envs/my_task")                        # doctest: +SKIP
>>> card = assert_resists("rewards.py:reward", data="rows.jsonl")  # doctest: +SKIP

``assert_resists`` raises ``AssertionError`` with one line per finding when any finding is at
least as severe as ``fail_on``, or when the scan is uncalibrated (a reference solution that does
not outscore the empty one makes every other number meaningless).
"""

from __future__ import annotations

from typing import Any

from hackfloor.core import Subject

__all__ = ["HackfloorFailure", "assert_resists", "run_scan"]


class HackfloorFailure(AssertionError):
    """A scan found a reward hack, or could not calibrate. ``card`` holds the integrity card."""

    def __init__(self, message: str, card: dict[str, Any]) -> None:
        super().__init__(message)
        self.card = card


def run_scan(
    target: str | Subject,
    *,
    probes: list[str] | None = None,
    replays: int = 1,
    seed: int = 0,
    **resolve_kwargs: Any,
) -> dict[str, Any]:
    """Scan ``target`` (anything ``hackfloor scan`` accepts, or a Subject) and return the card."""
    from hackfloor.adapters import resolve_subject
    from hackfloor.card import build_card
    from hackfloor.scan import ScanConfig, scan

    subject = (
        resolve_subject(target, seed=seed, **resolve_kwargs) if isinstance(target, str) else target
    )
    result = scan(subject, ScanConfig(replays=max(1, replays), seed=seed, probe_ids=probes))
    return build_card(result, command=f"hackfloor.testing.run_scan({target!r})")


def _describe(card: dict[str, Any], blocking: list[dict[str, Any]]) -> str:
    name = card.get("subject", {}).get("name", "subject")
    if card["verdict"] == "UNCALIBRATED":
        reasons = card["checks"]["hackfloor.calibration"].get("reasons") or ["no separation"]
        return f"hackfloor could not calibrate {name}: " + "; ".join(map(str, reasons))
    lines = [f"hackfloor found {len(blocking)} reward hack(s) in {name}:"]
    for p in blocking:
        hp = p.get("hack_pass", {})
        lines.append(
            f"  {p['id']} [{p['severity']}] {p['title']}: "
            f"hack-pass {hp.get('k')}/{hp.get('n')} tasks, mean gain {p['floor_gap']['mean']}"
        )
    return "\n".join(lines)


def assert_resists(
    target: str | Subject, *, fail_on: str = "high", **kwargs: Any
) -> dict[str, Any]:
    """Scan and fail unless every finding is below ``fail_on``. Returns the card."""
    from hackfloor.scan import SEVERITY_ORDER

    if fail_on not in ("critical", "high", "medium", "none"):
        raise ValueError("fail_on must be critical, high, medium or none")
    card = run_scan(target, **kwargs)
    blocking = [
        p
        for p in card["probes"]
        if p["status"] == "finding"
        and fail_on != "none"
        and SEVERITY_ORDER[p["severity"]] >= SEVERITY_ORDER[fail_on]
    ]
    if card["verdict"] == "UNCALIBRATED" or blocking:
        raise HackfloorFailure(_describe(card, blocking), card)
    return card
