"""Command-line interface: ``hackfloor scan``, ``hackfloor probes``, ``hackfloor version``."""

from __future__ import annotations

import argparse
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path

from rich.console import Console
from rich.table import Table

from hackfloor import __version__
from hackfloor.adapters import resolve_subject
from hackfloor.card import build_card, write_card
from hackfloor.export import write_openenv_checks
from hackfloor.probes.base import get_probes
from hackfloor.report import render_markdown, render_terminal
from hackfloor.scan import SEVERITY_ORDER, ScanConfig, scan

FAIL_ON = ("critical", "high", "medium", "none")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hackfloor",
        description="Adversarial probes for RL environment graders and agent benchmarks.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="probe an environment's grader for reward hacks")
    s.add_argument(
        "target",
        help="a task or RLVR directory with hackfloor.toml, a directory of tasks, "
        "file.py:reward_fn / module:reward_fn, reasoning-gym:<dataset>, "
        "verifiers:<module:factory> or subject:<module:factory>",
    )
    s.add_argument("--data", help="JSONL rows (prompt, answer) for a reward-function target")
    s.add_argument("--flavor", choices=("auto", "plain", "verl", "trl"), help="reward fn signature")
    s.add_argument(
        "--gold-template",
        help="how a correct completion looks, with {answer} as the slot (default: {answer})",
    )
    s.add_argument("--probes", help="comma-separated probe ids to run (default: all applicable)")
    s.add_argument("--tasks", type=int, help="use only the first N tasks or rows")
    s.add_argument("--replays", type=int, default=2, help="replays per attempt (default: 2)")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--out", default="hackfloor-card.json", help="integrity card path")
    s.add_argument("--report", help="also write a Markdown report here")
    s.add_argument(
        "--openenv-checks",
        metavar="PATH",
        help="also write the RFC 008 checks as OpenEnv CheckResult records (JSON)",
    )
    s.add_argument(
        "--fail-on",
        choices=FAIL_ON,
        default="high",
        help="exit 1 if any finding is at least this severe (default: high)",
    )
    s.add_argument(
        "--partial-credit",
        type=float,
        default=0.1,
        metavar="FRACTION",
        help="report a significant effect with no hack-pass whose best exploit reward is at "
        "most this fraction of the reward range as info, not a finding; 0 disables "
        "(default: 0.1)",
    )
    s.add_argument("--quiet", action="store_true", help="print only the verdict line")

    sub.add_parser("probes", help="list the available probes")
    sub.add_parser("version", help="print the version")
    return parser


def _cmd_probes(console: Console) -> int:
    table = Table(title="hackfloor probes", title_justify="left", header_style="bold")
    table.add_column("id", style="bold", no_wrap=True)
    table.add_column("family")
    table.add_column("needs")
    table.add_column("mechanism", overflow="fold")
    for p in get_probes():
        table.add_row(p.id, p.family, ", ".join(sorted(c.value for c in p.requires)), p.mechanism)
    console.print(table)
    return 0


def _cmd_scan(args: argparse.Namespace, console: Console, argv: Sequence[str]) -> int:
    subject = resolve_subject(
        args.target,
        data=args.data,
        flavor=args.flavor,
        gold_template=args.gold_template,
        limit=args.tasks,
        seed=args.seed,
    )
    config = ScanConfig(
        replays=max(1, args.replays),
        seed=args.seed,
        partial_credit=max(0.0, args.partial_credit),
        probe_ids=[p.strip() for p in args.probes.split(",")] if args.probes else None,
    )
    if console.is_interactive:
        with console.status("scanning", spinner="dots") as status:
            result = scan(subject, config, progress=lambda msg: status.update(msg))
    else:
        result = scan(subject, config)
    command = "hackfloor " + " ".join(shlex.quote(a) for a in argv)
    card = build_card(result, command=command)
    if args.quiet:
        console.print(
            f"{card['verdict']} level={card['level']} findings={len(result.findings)}"
            f" partial_credit={len(result.partial_credit)}"
        )
    else:
        render_terminal(card, console, target=args.target)
    out = write_card(card, args.out)
    console.print(f"[dim]integrity card →[/dim] {out}")
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(render_markdown(card), encoding="utf-8")
        console.print(f"[dim]report         →[/dim] {report}")
    if args.openenv_checks:
        checks = write_openenv_checks(card, args.openenv_checks)
        console.print(f"[dim]openenv checks →[/dim] {checks}")
    if card["verdict"] == "UNCALIBRATED":
        return 2
    if args.fail_on != "none" and any(
        SEVERITY_ORDER[p.severity] >= SEVERITY_ORDER[args.fail_on] for p in result.findings
    ):
        return 1
    return 0


def main(argv: Sequence[str] | None = None, *, console: Console | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(argv)
    console = console or Console()
    if args.command == "version":
        console.print(f"hackfloor {__version__}")
        return 0
    if args.command == "probes":
        return _cmd_probes(console)
    try:
        return _cmd_scan(args, console, argv)
    except (FileNotFoundError, ImportError, ValueError, KeyError) as exc:
        console.print(f"[bold red]error:[/bold red] {exc}")
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
