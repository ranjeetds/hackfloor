"""Rich terminal output for ``hackfloor scan``."""

from __future__ import annotations

from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_ICON = {
    "finding": ("✗ HACK", "bold red"),
    "resisted": ("✓ resisted", "green"),
    "flaky": ("~ flaky", "yellow"),
    "not_applicable": ("· n/a", "dim"),
    "error": ("! error", "magenta"),
}
_SEV = {"critical": "bold white on red", "high": "bold red", "medium": "yellow", "none": "dim"}
_VERDICT = {
    "VULNERABLE": "bold white on red",
    "WEAK": "bold black on yellow",
    "RESISTED": "bold white on green",
    "UNCALIBRATED": "bold white on magenta",
}


def render_terminal(card: dict[str, Any], console: Console, *, target: str = "") -> None:
    subj = card["subject"]
    cal = card["calibration"]
    s = card["summary"]
    header = Text.assemble(
        ("hackfloor ", "bold cyan"),
        (card["tool"]["version"], "cyan"),
        ("  ·  ", "dim"),
        (target or subj["name"], "bold"),
        ("  ·  ", "dim"),
        (f"{subj['framework']} · {s['tasks']} task{'s' if s['tasks'] != 1 else ''}", ""),
    )
    calib = Text.assemble(
        ("calibration  ", "dim"),
        ("reference ", ""),
        (f"{cal['gold_mean']:.2f}", "bold green"),
        ("   null policy ", ""),
        (f"{cal['null_mean']:.2f}", "bold"),
        ("   calibration ", ""),
        (
            card["checks"]["hackfloor.calibration"]["status"],
            "bold green"
            if card["checks"]["hackfloor.calibration"]["status"] == "PASS"
            else "bold red",
        ),
    )
    table = Table(box=None, pad_edge=False, show_edge=False, header_style="bold dim")
    table.add_column("probe", no_wrap=True)
    table.add_column("what it tries", overflow="fold")
    table.add_column("result", no_wrap=True)
    table.add_column("severity", no_wrap=True)
    table.add_column("Δ floor", justify="right", no_wrap=True)
    table.add_column("hack-pass", justify="right", no_wrap=True)
    for p in card["probes"]:
        label, style = _ICON[p["status"]]
        if p["status"] == "not_applicable":
            continue
        if p["status"] == "error":
            table.add_row(
                Text(p["id"], style="bold"), p.get("message", ""), Text(label, style=style)
            )
            continue
        hp = p["hack_pass"]
        table.add_row(
            Text(p["id"], style="bold"),
            p["title"],
            Text(label, style=style),
            Text(p["severity"] if p["severity"] != "none" else "–", style=_SEV[p["severity"]]),
            f"{p['floor_gap']['mean']:+.2f}",
            f"{hp['k']}/{hp['n']}",
        )
    level = "uncalibrated" if card["level"] is None else f"L{card['level']}"
    verdict = Text.assemble(
        (f" {card['verdict']} ", _VERDICT[card["verdict"]]),
        ("  ", ""),
        (f"{s['findings']} finding{'s' if s['findings'] != 1 else ''}", "bold"),
        (" · worst ", "dim"),
        (
            s["worst_severity"],
            _SEV[s["worst_severity"]].replace(" on red", "").replace("white", "red"),
        ),
        (f" · integrity level {level}", "bold"),
        (f" · {s['seconds']:.1f}s", "dim"),
    )
    console.print(Panel(Group(header, calib), border_style="cyan", padding=(0, 1)))
    console.print(table)
    skipped = [p["id"] for p in card["probes"] if p["status"] == "not_applicable"]
    if skipped:
        console.print(Text(f"not applicable to this target: {', '.join(skipped)}", style="dim"))
    console.print()
    console.print(verdict)
    for p in card["probes"]:
        ev = p.get("evidence")
        if p["status"] == "finding" and ev:
            where = f"  (task {ev['task']})" if s["tasks"] > 1 else ""
            console.print(
                Text.assemble(
                    ("  ↳ ", "dim"),
                    (f"{p['id']:<14}", "bold red"),
                    (f"{ev['variant']:<22}", ""),
                    ("scored ", "dim"),
                    (f"{ev['exploit_reward']:.2f}", "bold red"),
                    ("  control ", "dim"),
                    (f"{ev['control_reward']:.2f}", "bold"),
                    ("  reference ", "dim"),
                    (f"{ev['gold_reward']:.2f}", "green"),
                    (where, "dim"),
                )
            )
