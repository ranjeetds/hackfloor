"""Markdown report, suitable for a PR comment or an environment's README."""

from __future__ import annotations

from typing import Any

_STATUS = {
    "finding": "**hack**",
    "resisted": "resisted",
    "flaky": "flaky",
    "not_applicable": "n/a",
    "error": "error",
}


def _fmt(x: Any) -> str:
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:.2f}"
    return str(x)


def render_markdown(card: dict[str, Any]) -> str:
    s = card["summary"]
    cal = card["calibration"]
    subj = card["subject"]
    level = "uncalibrated" if card["level"] is None else f"L{card['level']}"
    lines = [
        f"# hackfloor report: `{subj['name']}`",
        "",
        f"**Verdict: {card['verdict']}** · level **{level}** · {s['findings']} finding(s), "
        f"worst severity **{s['worst_severity']}** · {s['tasks']} task(s) · "
        f"{s['probes_run']} probe(s) run",
        "",
        f"Calibration: reference solution scores {_fmt(cal['gold_mean'])}, the null policy "
        f"scores {_fmt(cal['null_mean'])} (reward range {cal['reward_range']}).",
        "",
        "## Probes",
        "",
        "| Probe | Family | Result | Severity | Floor gap Δ | Hack-pass | Basis |",
        "|---|---|---|---|---|---|---|",
    ]
    skipped = [p["id"] for p in card["probes"] if p["status"] == "not_applicable"]
    for p in card["probes"]:
        if p["status"] == "not_applicable":
            continue
        if p["status"] == "error":
            lines.append(
                f"| `{p['id']}` {p['title']} | {p['family']} | {_STATUS[p['status']]} | – | – | – "
                f"| {p.get('message', '')} |"
            )
            continue
        hp = p["hack_pass"]
        lines.append(
            f"| `{p['id']}` {p['title']} | {p['family']} | {_STATUS[p['status']]} | "
            f"{p['severity'] if p['severity'] != 'none' else '–'} | "
            f"{_fmt(p['floor_gap']['mean'])} | {hp['k']}/{hp['n']} | {p['decision']['basis']} |"
        )
    if skipped:
        lines += ["", f"Not applicable to this target: {', '.join(f'`{i}`' for i in skipped)}."]
    findings = [p for p in card["probes"] if p["status"] == "finding"]
    if findings:
        lines += ["", "## Findings", ""]
        for p in findings:
            ev = p.get("evidence", {})
            lines += [
                f"### `{p['id']}` {p['title']} ({p['severity']})",
                "",
                f"On task `{ev.get('task')}`, variant `{ev.get('variant')}` scored "
                f"{_fmt(ev.get('exploit_reward'))} against a matched control of "
                f"{_fmt(ev.get('control_reward'))} (reference solution: "
                f"{_fmt(ev.get('gold_reward'))}). Mean floor gap over {p['n_tasks']} task(s): "
                f"{_fmt(p['floor_gap']['mean'])} "
                f"(95% CI {_fmt(p['floor_gap']['ci95'][0])} to {_fmt(p['floor_gap']['ci95'][1])}).",
                "",
            ]
    lines += ["## Checks", "", "| Check | Status |", "|---|---|"]
    for key, chk in card["checks"].items():
        lines.append(f"| `{key}` | {chk['status']} |")
    lines += [
        "",
        "`NOT_MEASURED` means this version of hackfloor does not test that criterion yet; it is "
        "not a pass.",
        "",
        "---",
        "",
        f"hackfloor {card['tool']['version']} · card {card['card_version']} · {card['created_at']}",
    ]
    if card.get("reproduce"):
        lines += ["", "Reproduce:", "", "```bash", card["reproduce"], "```"]
    return "\n".join(lines) + "\n"
