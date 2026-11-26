"""Regenerate the README images from real scans of the bundled fixtures.

    uv run python scripts/render_readme_assets.py

Writes docs/assets/scan-vulnerable.svg, scan-fixed.svg and integrity-card-{light,dark}.svg.
Nothing in these images is typed by hand: they are rendered from the CLI output and the
integrity cards of the scans this script runs.
"""

from __future__ import annotations

import json
import os
import sys
from html import escape
from pathlib import Path

from rich.console import Console
from rich.terminal_theme import MONOKAI

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
OUT = ROOT / "hackfloor-out"

sys.path.insert(0, str(ROOT / "src"))
from hackfloor.cli import main  # noqa: E402


def record_scan(target: str, card_name: str, svg_name: str) -> dict:
    os.chdir(ROOT)
    console = Console(record=True, width=100, force_terminal=True, color_system="truecolor")
    console.print(f"[bold green]$[/bold green] hackfloor scan {target}")
    argv = ["scan", target, "--out", f"hackfloor-out/{card_name}", "--fail-on", "none"]
    main(argv, console=console)
    console.save_svg(str(ASSETS / svg_name), title=f"hackfloor scan {target}", theme=MONOKAI)
    return json.loads((OUT / card_name).read_text())


PALETTES = {
    "light": {
        "bg": "#ffffff",
        "panel": "#f6f8fa",
        "border": "#d0d7de",
        "text": "#1f2328",
        "muted": "#59636e",
        "red": "#cf222e",
        "green": "#1a7f37",
        "amber": "#9a6700",
        "grey": "#6e7781",
    },
    "dark": {
        "bg": "#0d1117",
        "panel": "#161b22",
        "border": "#30363d",
        "text": "#e6edf3",
        "muted": "#9198a1",
        "red": "#f85149",
        "green": "#3fb950",
        "amber": "#d29922",
        "grey": "#8b949e",
    },
}

FONT = "ui-sans-serif, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"


def _icon(cx: float, cy: float, ok: bool, pal: dict) -> str:
    color = pal["green"] if ok else pal["red"]
    if ok:
        mark = f"M{cx - 4} {cy} l3 3 l5 -6"
    else:
        mark = f"M{cx - 3.5} {cy - 3.5} l7 7 M{cx + 3.5} {cy - 3.5} l-7 7"
    return (
        f'<circle cx="{cx}" cy="{cy}" r="8" fill="{color}"/>'
        f'<path d="{mark}" stroke="#ffffff" stroke-width="2" fill="none" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def _card_svg(card: dict, x: float, pal: dict) -> str:
    verdict = card["verdict"]
    level = "n/a" if card["level"] is None else f"L{card['level']}"
    vcolor = pal["red"] if verdict == "VULNERABLE" else pal["green"]
    w, h = 450, 330
    parts = [
        f'<rect x="{x}" y="20" width="{w}" height="{h}" rx="12" fill="{pal["panel"]}" '
        f'stroke="{pal["border"]}"/>',
        f'<text x="{x + 24}" y="52" font-family="{FONT}" font-size="13" fill="{pal["muted"]}">'
        f"INTEGRITY CARD · {escape(card['subject']['framework']).upper()}</text>",
        f'<text x="{x + 24}" y="82" font-family="{MONO}" font-size="20" font-weight="700" '
        f'fill="{pal["text"]}">{escape(card["subject"]["name"])}</text>',
        f'<rect x="{x + 24}" y="98" width="{18 + 9.6 * len(verdict)}" height="26" rx="6" '
        f'fill="{vcolor}"/>',
        f'<text x="{x + 33}" y="116" font-family="{MONO}" font-size="14" font-weight="700" '
        f'fill="#ffffff">{verdict}</text>',
        f'<text x="{x + w - 24}" y="58" text-anchor="end" font-family="{FONT}" font-size="12" '
        f'fill="{pal["muted"]}">INTEGRITY LEVEL</text>',
        f'<text x="{x + w - 24}" y="104" text-anchor="end" font-family="{FONT}" font-size="44" '
        f'font-weight="800" fill="{vcolor}">{level}</text>',
        f'<line x1="{x + 24}" y1="140" x2="{x + w - 24}" y2="140" stroke="{pal["border"]}"/>',
    ]
    y = 166
    rows = [p for p in card["probes"] if p["status"] != "not_applicable"]
    for p in rows:
        hacked = p["status"] == "finding"
        color = pal["red"] if hacked else pal["green"]
        label = p["severity"] if hacked else "resisted"
        parts += [
            _icon(x + 32, y - 5, not hacked, pal),
            f'<text x="{x + 50}" y="{y}" font-family="{MONO}" font-size="13.5" '
            f'fill="{pal["text"]}">{p["id"]}</text>',
            f'<text x="{x + 178}" y="{y}" font-family="{FONT}" font-size="13" '
            f'fill="{pal["muted"]}">{escape(p["title"])}</text>',
            f'<text x="{x + w - 24}" y="{y}" text-anchor="end" font-family="{MONO}" '
            f'font-size="13" font-weight="700" fill="{color}">{label}</text>',
        ]
        y += 28
    sanity = card["checks"]["hackfloor.calibration"]["status"]
    rfc = {k: v for k, v in card["checks"].items() if not k.startswith("hackfloor.")}
    measured = sum(c["status"] != "NOT_MEASURED" for c in rfc.values())
    parts.append(
        f'<text x="{x + 24}" y="{y + 12}" font-family="{FONT}" font-size="12.5" '
        f'fill="{pal["muted"]}">calibration {sanity} · {measured} of '
        f"{len(rfc)} RFC 008 criteria measured by v0.1</text>"
    )
    return "\n".join(parts)


def integrity_cards(before: dict, after: dict) -> None:
    for mode, pal in PALETTES.items():
        svg = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="980" height="370" '
            'viewBox="0 0 980 370" role="img" aria-label="Integrity cards before and after '
            'fixing the verifier">',
            f'<rect width="980" height="370" fill="{pal["bg"]}" rx="14"/>',
            _card_svg(before, 20, pal),
            f'<path d="M476 185 h24 m-8 -8 l8 8 l-8 8" stroke="{pal["muted"]}" '
            'stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
            _card_svg(after, 510, pal),
            "</svg>",
        ]
        (ASSETS / f"integrity-card-{mode}.svg").write_text("\n".join(svg) + "\n")


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    before = record_scan(
        "fixtures/tasks/vulnerable_pytest", "vulnerable_pytest.json", "scan-vulnerable.svg"
    )
    after = record_scan("fixtures/tasks/fixed_pytest", "fixed_pytest.json", "scan-fixed.svg")
    record_scan("fixtures/rlvr/vulnerable_math", "vulnerable_math.json", "scan-rlvr.svg")
    integrity_cards(before, after)
    print("wrote", ", ".join(sorted(p.name for p in ASSETS.glob("*.svg"))))
