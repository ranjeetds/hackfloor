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
from rich.terminal_theme import TerminalTheme

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
OUT = ROOT / "hackfloor-out"

sys.path.insert(0, str(ROOT / "src"))
# The images use a fixed width. rich lets COLUMNS/LINES override an explicit width, and
# falls back to 80 columns when TERM is "dumb" (as in many CI and agent shells).
for _var in ("COLUMNS", "LINES"):
    os.environ.pop(_var, None)
if os.environ.get("TERM", "dumb") == "dumb":
    os.environ["TERM"] = "xterm-256color"
from hackfloor.cli import main  # noqa: E402


def record_scan(target: str, card_name: str, svg_name: str) -> dict:
    os.chdir(ROOT)
    console = Console(
        record=True,
        width=104,
        force_terminal=True,
        force_interactive=False,
        color_system="truecolor",
    )
    console.print(f"[bold green]$[/bold green] hackfloor scan {target}")
    argv = ["scan", target, "--out", f"hackfloor-out/{card_name}", "--fail-on", "none"]
    main(argv, console=console)
    console.save_svg(str(ASSETS / svg_name), title=f"hackfloor scan {target}", theme=MUTED_THEME)
    _mute_scan_svg(ASSETS / svg_name)
    return json.loads((OUT / card_name).read_text())


# Research-paper palette (same values as the launch visuals).
# Dark contrast vs #1B1D1F: text 13.3:1, muted 6.8:1, accent 4.7:1, red 5.1:1.
# Badge solids with white text: accent-solid 4.7:1, red-solid 5.1:1 (WCAG AA).
# Light contrast vs #F4F3F0: text 12.5:1, muted 5.6:1, accent 6.3:1, red 5.2:1.
PALETTES = {
    "light": {
        "bg": "#F4F3F0",
        "panel": "#EBEAE6",
        "border": "#D4D2CC",
        "text": "#2C2D2B",
        "muted": "#5F615E",
        "red": "#A14D48",
        "red_solid": "#A14D48",
        "green": "#3D5F5C",
        "accent_solid": "#3D5F5C",
        "amber": "#8A6A32",
        "grey": "#8A8C89",
    },
    "dark": {
        "bg": "#1B1D1F",
        "panel": "#242628",
        "border": "#3C3F44",
        "text": "#E6E4DF",
        "muted": "#A3A5A2",
        "red": "#C17A74",
        "red_solid": "#A35A55",
        "green": "#6A8E89",
        "accent_solid": "#5A7A76",
        "amber": "#B3925A",
        "grey": "#8A8C89",
    },
}

FONT = "ui-sans-serif, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"



def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# Muted ANSI theme for the README scan SVGs only (the live CLI is unchanged).
# Red/amber are reserved for findings; pass/info map to muted teal.
_TEAL = _rgb("6A8E89")
_RED = _rgb("C17A74")
_AMBER = _rgb("B3925A")
_FG = _rgb("E6E4DF")
MUTED_THEME = TerminalTheme(
    background=_rgb("1B1D1F"),
    foreground=_FG,
    normal=[
        _rgb("1B1D1F"),
        _RED,
        _TEAL,
        _AMBER,
        _TEAL,
        _rgb("A37A76"),
        _TEAL,
        _FG,
    ],
    bright=[
        _rgb("3C3F44"),
        _RED,
        _TEAL,
        _AMBER,
        _TEAL,
        _rgb("A37A76"),
        _TEAL,
        (255, 255, 255),
    ],
)


def _mute_scan_svg(path: Path) -> None:
    """Darken badge backgrounds so white label text meets WCAG AA, and mute chrome dots."""
    text = path.read_text()
    import re
    text = re.sub(r'<rect fill="#c17a74"', '<rect fill="#A35A55"', text, flags=re.I)
    text = re.sub(r'<rect fill="#6a8e89"', '<rect fill="#5A7A76"', text, flags=re.I)
    text = re.sub(r'<rect fill="#b3925a"', '<rect fill="#8A6A32"', text, flags=re.I)
    text = text.replace('fill="#ff5f57"', 'fill="#8A6562"')
    text = text.replace('fill="#febc2e"', 'fill="#8A7A52"')
    text = text.replace('fill="#28c840"', 'fill="#5A7A76"')
    path.write_text(text)

def _icon(cx: float, cy: float, ok: bool, pal: dict) -> str:
    color = pal["accent_solid"] if ok else pal["red_solid"]
    if ok:
        mark = f"M{cx - 4} {cy} l3 3 l5 -6"
    else:
        mark = f"M{cx - 3.5} {cy - 3.5} l7 7 M{cx + 3.5} {cy - 3.5} l-7 7"
    return (
        f'<circle cx="{cx}" cy="{cy}" r="8" fill="{color}"/>'
        f'<path d="{mark}" stroke="#ffffff" stroke-width="2" fill="none" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def card_height(card: dict) -> int:
    rows = sum(p["status"] != "not_applicable" for p in card["probes"])
    return 166 + 28 * rows + 20


def _short(title: str, limit: int = 27) -> str:
    return title if len(title) <= limit else title[: limit - 1].rstrip() + "…"


def _card_svg(card: dict, x: float, pal: dict) -> str:
    verdict = card["verdict"]
    level = "n/a" if card["level"] is None else f"L{card['level']}"
    vcolor = pal["red"] if verdict == "VULNERABLE" else pal["green"]
    vfill = pal["red_solid"] if verdict == "VULNERABLE" else pal["accent_solid"]
    rows = [p for p in card["probes"] if p["status"] != "not_applicable"]
    w, h = 450, card_height(card)
    parts = [
        f'<rect x="{x}" y="20" width="{w}" height="{h}" rx="12" fill="{pal["panel"]}" '
        f'stroke="{pal["border"]}"/>',
        f'<text x="{x + 24}" y="52" font-family="{FONT}" font-size="13" fill="{pal["muted"]}">'
        f"INTEGRITY CARD · {escape(card['subject']['framework']).upper()}</text>",
        f'<text x="{x + 24}" y="82" font-family="{MONO}" font-size="20" font-weight="700" '
        f'fill="{pal["text"]}">{escape(card["subject"]["name"])}</text>',
        f'<rect x="{x + 24}" y="98" width="{18 + 9.6 * len(verdict)}" height="26" rx="6" '
        f'fill="{vfill}"/>',
        f'<text x="{x + 33}" y="116" font-family="{MONO}" font-size="14" font-weight="700" '
        f'fill="#ffffff">{verdict}</text>',
        f'<text x="{x + w - 24}" y="58" text-anchor="end" font-family="{FONT}" font-size="12" '
        f'fill="{pal["muted"]}">INTEGRITY LEVEL</text>',
        f'<text x="{x + w - 24}" y="104" text-anchor="end" font-family="{FONT}" font-size="44" '
        f'font-weight="800" fill="{vcolor}">{level}</text>',
        f'<line x1="{x + 24}" y1="140" x2="{x + w - 24}" y2="140" stroke="{pal["border"]}"/>',
    ]
    y = 166
    for p in rows:
        hacked = p["status"] == "finding"
        color = pal["red"] if hacked else pal["green"]
        label = p["severity"] if hacked else "resisted"
        parts += [
            _icon(x + 32, y - 5, not hacked, pal),
            f'<text x="{x + 50}" y="{y}" font-family="{MONO}" font-size="13.5" '
            f'fill="{pal["text"]}">{p["id"]}</text>',
            f'<text x="{x + 178}" y="{y}" font-family="{FONT}" font-size="13" '
            f'fill="{pal["muted"]}">{escape(_short(p["title"]))}</text>',
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
        f"{len(rfc)} RFC 008 criteria measured by v0.2</text>"
    )
    return "\n".join(parts)


def integrity_cards(before: dict, after: dict) -> None:
    height = max(card_height(before), card_height(after)) + 40
    mid = height // 2
    for mode, pal in PALETTES.items():
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="980" height="{height}" '
            f'viewBox="0 0 980 {height}" role="img" aria-label="Integrity cards before and after '
            'fixing the verifier">',
            f'<rect width="980" height="{height}" fill="{pal["bg"]}" rx="14"/>',
            _card_svg(before, 20, pal),
            f'<path d="M476 {mid} h24 m-8 -8 l8 8 l-8 8" stroke="{pal["muted"]}" '
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
