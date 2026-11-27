"""Guards for the documentation: tables that render, and counts that match the code."""

import re
from pathlib import Path

import pytest

from hackfloor.probes.base import get_probes

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}


def _is_row(line: str) -> bool:
    return line.startswith("|") and line.rstrip().endswith("|")


def _is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:|-]+\|", line.strip()))


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_table_row_is_cut_off_by_a_blank_line(path):
    """A blank line inside a table ends it, and the rest of its rows show as plain text."""
    lines = path.read_text(encoding="utf-8").splitlines()
    in_code = False
    broken = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        if in_code or i < 2:
            continue
        starts_table = i + 1 < len(lines) and _is_separator(lines[i + 1])
        if (
            _is_row(line)
            and not _is_separator(line)
            and lines[i - 1] == ""
            and _is_row(lines[i - 2])
            and not starts_table
        ):
            broken.append(i + 1)
    assert not broken, f"{path.name}: table row after a blank line at line(s) {broken}"


def test_probes_page_lists_every_probe_in_a_table_row():
    text = (ROOT / "docs" / "probes.md").read_text(encoding="utf-8")
    rows = {m.group(1) for m in re.finditer(r"^\| `(HF-[A-Z]+)` \|", text, re.MULTILINE)}
    assert rows == {p.id for p in get_probes()}


def test_readme_probe_counts_match_the_code():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    total = len(get_probes())
    assert f"{total} probes in five families" in readme
    shown = len(set(re.findall(r"\| `(HF-[A-Z]+)` \|", readme.split("## Installation")[0])))
    match = re.search(r"runs these and (\w+) more", readme)
    assert match, "the README should say how many more probes there are"
    assert WORDS[match.group(1)] == total - shown
