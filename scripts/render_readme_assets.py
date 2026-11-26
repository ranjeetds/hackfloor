"""Regenerate the README and docs images from real scans.

    python scripts/render_readme_assets.py

Needs ``playwright`` with Chromium installed (a development tool, not a runtime dependency)
and, for the hero image, ``reasoning-gym==0.1.25`` (``pip install "hackfloor[reasoning-gym]"``).
Without reasoning-gym the hero image is left as it is.

Writes, for ``light`` and ``dark``, into docs/assets/:

    hero-<mode>.png               scan of reasoning-gym 0.1.25 ``game_of_life_halting``
    scan-vulnerable-<mode>.png    scan of the vulnerable pytest fixture
    integrity-card-<mode>.png     integrity cards of the vulnerable and fixed pytest fixtures

Nothing in these images is typed by hand: they are rendered from the output of the CLI
renderer and from the integrity cards of the scans this script runs. Images are PNG at 3x so
they stay sharp at the width GitHub shows them, and they do not depend on the reader's fonts.

Palette (contrast ratios are against the image background; AA needs 4.5 for text):
    light  bg #FFFFFF  panel #F6F8FA  border #D0D7DE  text #1F2328 (15.8)  muted #59636E (6.1)
           accent #3730A3 (9.9)  red #B42318 (6.6)  amber #8A5A00 (5.9)
    dark   bg #0D1117  panel #161B22  border #30363D  text #E6EDF3 (16.0)  muted #9198A1 (6.5)
           accent #A5B4FC (9.5)  red #F08278 (7.4)   amber #E3B341 (9.7)
    Badge solids with white text: accent #3730A3 (9.9) / #4F46E5 (6.3), red #B42318 (6.6).
"""

# ruff: noqa: E501  (embedded CSS and HTML lines are long)
from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from html import escape
from pathlib import Path

from rich.console import Console
from rich.terminal_theme import TerminalTheme
from rich.text import Text

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
from hackfloor.report.terminal import render_terminal  # noqa: E402

PALETTES = {
    "light": {
        "bg": "#FFFFFF",
        "panel": "#F6F8FA",
        "border": "#D0D7DE",
        "text": "#1F2328",
        "muted": "#59636E",
        "accent": "#3730A3",
        "accent_solid": "#3730A3",
        "red": "#B42318",
        "red_solid": "#B42318",
        "amber": "#8A5A00",
        "dot": "#C4CAD1",
    },
    "dark": {
        "bg": "#0D1117",
        "panel": "#161B22",
        "border": "#30363D",
        "text": "#E6EDF3",
        "muted": "#9198A1",
        "accent": "#A5B4FC",
        "accent_solid": "#4F46E5",
        "red": "#F08278",
        "red_solid": "#B42318",
        "amber": "#E3B341",
        "dot": "#3D444D",
    },
}
SANS = "Inter, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = (
    "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
)


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rich_theme(pal: dict) -> TerminalTheme:
    """ANSI colours for the image. Only red, yellow, blue and magenta carry meaning."""
    fg, text_on_solid = _rgb(pal["text"]), (255, 255, 255)
    normal = [
        _rgb(pal["bg"]),
        _rgb(pal["red"]),
        fg,
        _rgb(pal["amber"]),
        _rgb(pal["accent"]),
        _rgb(pal["accent"]),
        _rgb(pal["accent"]),
        text_on_solid,
    ]
    return TerminalTheme(_rgb(pal["bg"]), fg, normal, normal)


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(int(x + (y - x) * t) for x, y in zip(a, b, strict=True)))


def run_scan(target: str, card_name: str) -> dict:
    os.chdir(ROOT)
    OUT.mkdir(exist_ok=True)
    quiet = Console(file=io.StringIO(), width=120)
    argv = ["scan", target, "--out", f"hackfloor-out/{card_name}", "--fail-on", "none"]
    if target.startswith("reasoning-gym:"):
        argv += ["--tasks", "100", "--replays", "2", "--seed", "0"]
    main(argv, console=quiet)
    return json.loads((OUT / card_name).read_text())


def terminal_html(card: dict, target: str, pal: dict) -> str:
    """The CLI's own renderer, recorded and exported with the palette's ANSI theme."""
    console = Console(
        record=True,
        width=100,
        force_terminal=True,
        force_interactive=False,
        color_system="truecolor",
        file=io.StringIO(),
    )
    console.print(Text.assemble(("$ ", "dim"), ("hackfloor scan ", "bold"), (target, "bold")))
    render_terminal(card, console, target=target)
    theme = rich_theme(pal)
    html = console.export_html(
        theme=theme,
        inline_styles=True,
        code_format='<pre class="t"><code>{code}</code></pre>',
    )
    # rich draws "dim" as a 50% blend, which is below AA contrast; use the muted colour.
    fg, bg = _rgb(pal["text"]), _rgb(pal["bg"])
    html = html.replace(f"color: {_blend(fg, bg, 0.5)}", f"color: {pal['muted']}")
    # Badges ("white on red", "white on blue") need dark solids for white text; the ANSI
    # red and blue of the dark theme are the light tints used for text, so swap the fills.
    for ansi, solid in ((pal["red"], pal["red_solid"]), (pal["accent"], pal["accent_solid"])):
        html = html.replace(
            f"background-color: {ansi.lower()}", f"background-color: {solid.lower()}"
        )
    return html


def window_page(inner: str, pal: dict, width: int = 828) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:transparent}}
body{{padding:0;font-family:{MONO}}}
.win{{width:{width}px;background:{pal["bg"]};border:1px solid {pal["border"]};border-radius:12px;overflow:hidden}}
.bar{{height:34px;background:{pal["panel"]};border-bottom:1px solid {pal["border"]};display:flex;align-items:center;gap:7px;padding-left:16px}}
.bar i{{width:11px;height:11px;border-radius:50%;background:{pal["dot"]};display:block}}
pre.t{{font-family:{MONO};font-size:13px;line-height:1.55;padding:18px 24px 22px;color:{pal["text"]};background:{pal["bg"]};white-space:pre;font-variant-ligatures:none}}
pre.t code{{font-family:inherit}}
</style></head><body><div class="win" id="shot"><div class="bar"><i></i><i></i><i></i></div>
{inner}</div></body></html>"""


def card_html(card: dict, pal: dict) -> str:
    verdict = card["verdict"]
    level = "n/a" if card["level"] is None else f"L{card['level']}"
    bad = verdict == "VULNERABLE"
    rows = []
    for p in card["probes"]:
        if p["status"] == "not_applicable":
            continue
        hacked = p["status"] == "finding"
        mark = "&#10005;" if hacked else "&#10003;"
        solid = pal["red_solid"] if hacked else pal["accent_solid"]
        label = p["severity"] if hacked else "resisted"
        color = pal["red"] if hacked else pal["muted"]
        title = p["title"]
        rows.append(
            f'<div class="row"><span class="ic" style="background:{solid}">{mark}</span>'
            f'<span class="pid">{p["id"]}</span><span class="ttl">{escape(title)}</span>'
            f'<span class="lab" style="color:{color}">{label}</span></div>'
        )
    rfc = {k: v for k, v in card["checks"].items() if not k.startswith("hackfloor.")}
    measured = sum(c["status"] != "NOT_MEASURED" for c in rfc.values())
    sanity = card["checks"]["hackfloor.calibration"]["status"]
    vfill = pal["red_solid"] if bad else pal["accent_solid"]
    lvl = pal["red"] if bad else pal["text"]
    return (
        f'<div class="card"><div class="head"><div><div class="eyebrow">INTEGRITY CARD · '
        f"{escape(card['subject']['framework']).upper()}</div>"
        f'<div class="name">{escape(card["subject"]["name"])}</div>'
        f'<span class="badge" style="background:{vfill}">{verdict}</span></div>'
        f'<div class="lvl"><div class="eyebrow">INTEGRITY LEVEL</div>'
        f'<div class="big" style="color:{lvl}">{level}</div></div></div>'
        f'<div class="rows">{"".join(rows)}</div>'
        f'<div class="foot">calibration {sanity} · {measured} of {len(rfc)} RFC 008 criteria measured</div></div>'
    )


def cards_page(before: dict, after: dict, pal: dict) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:transparent}}
.wrap{{display:flex;align-items:center;gap:18px;padding:22px;background:{pal["bg"]};border:1px solid {pal["border"]};border-radius:12px;width:max-content;font-family:{SANS}}}
.card{{width:470px;background:{pal["panel"]};border:1px solid {pal["border"]};border-radius:10px;padding:22px 24px;color:{pal["text"]};align-self:stretch;display:flex;flex-direction:column}}
.head{{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:16px;border-bottom:1px solid {pal["border"]}}}
.eyebrow{{font-size:11.5px;letter-spacing:.06em;color:{pal["muted"]}}}
.name{{font-family:{MONO};font-size:19px;font-weight:700;margin:6px 0 12px}}
.badge{{display:inline-block;font-family:{MONO};font-size:13px;font-weight:700;color:#fff;padding:4px 10px;border-radius:6px}}
.lvl{{text-align:right}}
.big{{font-size:42px;font-weight:800;line-height:1.1;margin-top:4px}}
.rows{{padding-top:8px;flex:1}}
.row{{display:flex;align-items:center;gap:10px;height:27px;font-size:13px}}
.ic{{width:16px;height:16px;border-radius:50%;color:#fff;font-size:10px;line-height:16px;text-align:center;font-weight:700;flex:none}}
.pid{{font-family:{MONO};font-size:13px;width:116px;flex:none}}
.lab{{width:68px;text-align:right;flex:none}}
.ttl{{color:{pal["muted"]};flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.lab{{font-family:{MONO};font-weight:700;font-size:12.5px}}
.foot{{margin-top:14px;font-size:12px;color:{pal["muted"]}}}
.arrow{{color:{pal["muted"]};font-size:26px}}
</style></head><body><div class="wrap" id="shot">{card_html(before, pal)}<div class="arrow">&rarr;</div>{card_html(after, pal)}</div></body></html>"""


async def screenshot(pages: dict[Path, str]) -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            device_scale_factor=3, viewport={"width": 1100, "height": 900}
        )
        for path, html in pages.items():
            page = await ctx.new_page()
            await page.set_content(html)
            await page.evaluate("document.fonts.ready")
            await page.locator("#shot").screenshot(path=str(path), omit_background=True)
            await page.close()
            print("wrote", path.relative_to(ROOT))
        await browser.close()


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    pages: dict[Path, str] = {}
    vuln = run_scan("fixtures/tasks/vulnerable_pytest", "vulnerable_pytest.json")
    fixed = run_scan("fixtures/tasks/fixed_pytest", "fixed_pytest.json")
    hero = None
    try:
        import reasoning_gym  # noqa: F401

        hero = run_scan("reasoning-gym:game_of_life_halting", "game_of_life_halting.json")
    except ImportError:
        print("reasoning-gym is not installed: leaving hero-*.png unchanged")
    for mode, pal in PALETTES.items():
        pages[ASSETS / f"scan-vulnerable-{mode}.png"] = window_page(
            terminal_html(vuln, "fixtures/tasks/vulnerable_pytest", pal), pal
        )
        pages[ASSETS / f"integrity-card-{mode}.png"] = cards_page(vuln, fixed, pal)
        if hero is not None:
            pages[ASSETS / f"hero-{mode}.png"] = window_page(
                terminal_html(hero, "reasoning-gym:game_of_life_halting", pal), pal
            )
    asyncio.run(screenshot(pages))
