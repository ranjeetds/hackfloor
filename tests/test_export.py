import json
import re

from hackfloor import scan
from hackfloor.adapters import resolve_subject
from hackfloor.card import build_card
from hackfloor.cli import main
from hackfloor.export import openenv_check_results
from hackfloor.scan import ScanConfig

ID = re.compile(r"^[a-z_]+\.[a-z_]+$")
FIELDS = {"check_id", "status", "measured", "evidence", "remediation", "duration_s"}


def _card(path):
    return build_card(scan(resolve_subject(str(path)), ScanConfig(replays=1)))


def test_check_results_shape(fixtures):
    results = openenv_check_results(_card(fixtures / "rlvr" / "vulnerable_math"))
    by_id = {r["check_id"]: r for r in results}
    for r in results:
        assert set(r) == FIELDS
        assert ID.match(r["check_id"])
        assert r["status"] in {"pass", "fail", "skip", "error"}
        assert r["duration_s"] >= 0
        assert all(isinstance(line, str) for line in r["evidence"])
    assert "hackfloor.calibration" not in by_id
    floor = by_id["statistical.adversarial_floor"]
    assert floor["status"] == "fail" and floor["remediation"]
    assert any(line.startswith("HF-DUMP (critical)") for line in floor["evidence"])
    assert by_id["semantic.oracle_max"]["status"] == "pass"
    assert by_id["semantic.oracle_max"]["remediation"] is None
    assert by_id["runtime.network_policy"]["status"] == "skip"
    assert by_id["runtime.network_policy"]["evidence"][0].startswith("not measured:")


def test_uncalibrated_card_never_passes(fixtures):
    card = _card(fixtures / "rlvr" / "fixed_math")
    card["checks"]["hackfloor.calibration"]["status"] = "FAIL"
    results = openenv_check_results(card)
    assert {r["status"] for r in results} == {"skip"}
    assert results[0]["evidence"][0].startswith("uncalibrated")


def test_cli_writes_openenv_checks(fixtures, tmp_path):
    out = tmp_path / "checks.json"
    code = main(
        [
            "scan",
            str(fixtures / "rlvr" / "fixed_math"),
            "--replays",
            "1",
            "--out",
            str(tmp_path / "card.json"),
            "--openenv-checks",
            str(out),
            "--quiet",
        ]
    )
    assert code == 0
    payload = json.loads(out.read_text())
    assert payload["source"] == "hackfloor"
    assert {c["check_id"] for c in payload["checks"]} >= {
        "statistical.adversarial_floor",
        "statistical.gameability_gap",
        "semantic.no_solution_leakage",
    }
