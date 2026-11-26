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
    assert checks["semantic.canary_floor"]["status"] == "NOT_MEASURED"
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
