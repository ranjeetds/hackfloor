import json

import jsonschema
import pytest

from hackfloor import scan
from hackfloor.adapters import resolve_subject
from hackfloor.card import build_card, card_schema
from hackfloor.cli import main
from hackfloor.report import render_markdown
from hackfloor.scan import ScanConfig


@pytest.mark.parametrize("name", ["vulnerable_math", "fixed_math"])
def test_card_validates_against_schema(fixtures, name):
    result = scan(resolve_subject(str(fixtures / "rlvr" / name)), ScanConfig(replays=1))
    card = build_card(result, command="hackfloor scan x")
    jsonschema.validate(card, card_schema())
    checks = card["checks"]
    assert checks["semantic.oracle_max"]["status"] == "PASS"
    assert checks["semantic.floor_gap"]["status"] == "PASS"
    assert checks["semantic.no_solution_leakage"]["status"] == "PASS"
    assert checks["semantic.canary_floor"]["status"] == "PASS"
    assert checks["semantic.canary_floor"]["probes_run"] == ["HF-WRONG"]
    expected = "FAIL" if name == "vulnerable_math" else "PASS"
    assert checks["statistical.adversarial_floor"]["status"] == expected
    gap = checks["statistical.gameability_gap"]
    assert gap["status"] == expected
    assert gap["correlation"] == (1.0 if name == "fixed_math" else gap["correlation"])
    assert gap["correlation"] < 0.9 if name == "vulnerable_math" else True
    md = render_markdown(card)
    assert md.startswith("# hackfloor report")
    assert ("## Findings" in md) == (name == "vulnerable_math")


def test_cli_exit_codes_and_outputs(fixtures, tmp_path, capsys):
    card = tmp_path / "card.json"
    report = tmp_path / "report.md"
    rc = main(
        [
            "scan",
            str(fixtures / "rlvr" / "vulnerable_math"),
            "--out",
            str(card),
            "--report",
            str(report),
            "--replays",
            "1",
        ]
    )
    assert rc == 1
    data = json.loads(card.read_text())
    assert data["verdict"] == "VULNERABLE"
    assert "HF-DUMP" in report.read_text()

    rc = main(
        [
            "scan",
            str(fixtures / "rlvr" / "vulnerable_math"),
            "--out",
            str(card),
            "--fail-on",
            "none",
            "--quiet",
        ]
    )
    assert rc == 0

    rc = main(["scan", str(fixtures / "rlvr" / "fixed_math"), "--out", str(card), "--quiet"])
    assert rc == 0


def test_cli_reward_function_target(fixtures, tmp_path):
    target = f"{fixtures / 'rlvr' / 'vulnerable_math' / 'reward.py'}:reward"
    rc = main(
        [
            "scan",
            target,
            "--data",
            str(fixtures / "rlvr" / "vulnerable_math" / "data.jsonl"),
            "--gold-template",
            "<answer>{answer}</answer>",
            "--probes",
            "HF-DUMP",
            "--out",
            str(tmp_path / "c.json"),
            "--quiet",
        ]
    )
    assert rc == 1


def test_cli_bad_target(tmp_path):
    assert main(["scan", str(tmp_path / "missing"), "--out", str(tmp_path / "c.json")]) == 2


def test_probes_and_version_commands(capsys):
    assert main(["probes"]) == 0
    assert "HF-CONFTEST" in capsys.readouterr().out
    assert main(["version"]) == 0


@pytest.mark.parametrize("name", ["vulnerable_math", "fixed_math"])
def test_terminal_output_uses_no_green_or_teal(fixtures, tmp_path, name):
    import re

    from rich.console import Console

    console = Console(force_terminal=True, color_system="standard", width=100)
    with console.capture() as capture:
        main(
            ["scan", str(fixtures / "rlvr" / name), "--out", str(tmp_path / "c.json")],
            console=console,
        )
    codes = {c for seq in re.findall(r"\x1b\[([0-9;]*)m", capture.get()) for c in seq.split(";")}
    # 32/92 green, 36/96 cyan, 42/102 and 46/106 their backgrounds
    assert not codes & {"32", "92", "36", "96", "42", "102", "46", "106"}


def _console():
    import io

    from rich.console import Console

    buffer = io.StringIO()
    return Console(file=buffer, width=200, force_terminal=False), buffer


def _write_reward_project(tmp_path, source):
    (tmp_path / "reward.py").write_text(source, encoding="utf-8")
    rows = [{"prompt": f"What is {n}+1?", "answer": str(n + 1)} for n in range(6)]
    (tmp_path / "rows.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return str(tmp_path / "reward.py") + ":reward", str(tmp_path / "rows.jsonl")


RAISING_REWARD = """
def reward(completion, answer):
    return 1.0 if int(completion.strip()) == int(answer) else 0.0
"""


def test_grader_that_raises_on_probe_outputs_is_inconclusive_not_resisted(tmp_path):
    target, data = _write_reward_project(tmp_path, RAISING_REWARD)
    console, out = _console()
    card_path = tmp_path / "card.json"
    rc = main(["scan", target, "--data", data, "--out", str(card_path)], console=console)
    text = out.getvalue()
    card = json.loads(card_path.read_text())
    jsonschema.validate(card, card_schema())
    assert rc == 2
    assert card["verdict"] == "INCONCLUSIVE"
    assert card["level"] == 0
    errored = [p for p in card["probes"] if p["status"] == "error"]
    assert {p["id"] for p in errored} >= {"HF-DUMP", "HF-ECHO", "HF-EMPTY"}
    assert errored[0]["failed_attempts"]["failed"] == errored[0]["failed_attempts"]["of"]
    assert "invalid literal for int()" in errored[0]["failed_attempts"]["first_error"]
    assert card["checks"]["runtime.reward_well_formed"]["status"] == "FAIL"
    floor = card["checks"]["statistical.adversarial_floor"]
    assert floor["status"] == "NOT_MEASURED"
    assert "HF-DUMP" in floor["not_evaluated"]
    # The terminal says how many calls failed and shows one example.
    assert "INCONCLUSIVE" in text
    assert "grader call(s) failed" in text
    assert "invalid literal for int()" in text
    assert "RESISTED" not in text


def test_reward_that_returns_none_is_inconclusive(tmp_path):
    source = """
def reward(completion, answer):
    if completion.strip() == str(answer):
        return 1.0
"""
    target, data = _write_reward_project(tmp_path, source)
    card_path = tmp_path / "card.json"
    console, _ = _console()
    assert main(["scan", target, "--data", data, "--out", str(card_path)], console=console) == 2
    assert json.loads(card_path.read_text())["verdict"] == "INCONCLUSIVE"


def test_quiet_output_reports_the_grader_error_count(tmp_path):
    target, data = _write_reward_project(tmp_path, RAISING_REWARD)
    console, out = _console()
    main(
        ["scan", target, "--data", data, "--out", str(tmp_path / "c.json"), "--quiet"],
        console=console,
    )
    line = out.getvalue().splitlines()[0]
    assert line.startswith("INCONCLUSIVE level=0")
    assert "grader_errors=" in line


def test_a_few_grader_errors_do_not_hide_a_real_result(tmp_path):
    # Raises on the empty answer only (the null policy), so most attempts are well formed.
    source = """
def reward(completion, answer):
    if not completion.strip():
        raise ValueError("empty answer")
    return 1.0 if str(answer) in completion else 0.0
"""
    target, data = _write_reward_project(tmp_path, source)
    card_path = tmp_path / "card.json"
    console, out = _console()
    rc = main(["scan", target, "--data", data, "--out", str(card_path)], console=console)
    card = json.loads(card_path.read_text())
    assert card["verdict"] == "VULNERABLE"
    assert rc == 1
    assert "grader call(s) failed" in out.getvalue()


def test_clean_scans_print_no_error_line(fixtures, tmp_path):
    console, out = _console()
    main(
        ["scan", str(fixtures / "rlvr" / "fixed_math"), "--out", str(tmp_path / "c.json")],
        console=console,
    )
    assert "grader call(s) failed" not in out.getvalue()
    assert "RESISTED" in out.getvalue()


def test_assert_resists_fails_on_an_inconclusive_scan(tmp_path):
    from hackfloor.testing import HackfloorFailure, assert_resists

    target, data = _write_reward_project(tmp_path, RAISING_REWARD)
    with pytest.raises(HackfloorFailure, match="could not evaluate"):
        assert_resists(target, data=data)


def test_error_text_with_square_brackets_is_printed_verbatim(monkeypatch):
    import hackfloor.cli as cli

    def fail(*args, **kwargs):
        raise ImportError("the adapter needs `pip install hackfloor[reasoning-gym]` [/oops]")

    monkeypatch.setattr(cli, "resolve_subject", fail)
    console, out = _console()
    assert main(["scan", "reasoning-gym:x"], console=console) == 2
    assert (
        "error: the adapter needs `pip install hackfloor[reasoning-gym]` [/oops]" in out.getvalue()
    )


@pytest.mark.parametrize("target", ["x[/y].py:fn", "dir[1]/x.py:fn", "[bold]x.py:fn"])
def test_scan_target_with_brackets_gives_a_plain_error(target, tmp_path):
    rows = tmp_path / "rows.jsonl"
    rows.write_text('{"prompt": "a", "answer": "1"}\n', encoding="utf-8")
    console, out = _console()
    assert main(["scan", target, "--data", str(rows)], console=console) == 2
    text = out.getvalue()
    assert text.startswith("error:")
    assert target.split(":")[0] in text


def test_square_brackets_survive_in_the_terminal_report_and_paths(fixtures, tmp_path):
    from hackfloor.report import render_terminal

    card = json.loads(
        _scan_to_card(fixtures / "rlvr" / "fixed_math", tmp_path).read_text(encoding="utf-8")
    )
    probe = next(p for p in card["probes"] if p["status"] == "resisted")
    probe.clear()
    probe.update(
        id="HF-X", family="form", title="t", status="error", severity="none", message="bad [/x]"
    )
    console, out = _console()
    render_terminal(card, console)
    assert "bad [/x]" in out.getvalue()

    odd = tmp_path / "out [1]" / "card.json"
    console, out = _console()
    main(
        ["scan", str(fixtures / "rlvr" / "fixed_math"), "--out", str(odd), "--quiet"],
        console=console,
    )
    assert "out [1]" in out.getvalue()


def _scan_to_card(path, tmp_path):
    out = tmp_path / "card-for-render.json"
    console, _ = _console()
    main(["scan", str(path), "--out", str(out), "--quiet"], console=console)
    return out


def test_probes_listing_does_not_parse_markup(monkeypatch):
    import types

    import hackfloor.cli as cli

    fake = types.SimpleNamespace(
        id="HF-X", family="form", requires=set(), mechanism="writes [/bold] and [red]text[/red]"
    )
    monkeypatch.setattr(cli, "get_probes", lambda: [fake])
    console, out = _console()
    assert main(["probes"], console=console) == 0
    assert "[/bold]" in out.getvalue()
    assert "[red]text[/red]" in out.getvalue()
