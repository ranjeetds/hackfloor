import pytest

from hackfloor.testing import HackfloorFailure, assert_resists, run_scan

pytest_plugins = ["pytester"]


def test_assert_resists_passes_and_returns_the_card(fixtures):
    card = assert_resists(str(fixtures / "rlvr" / "fixed_math"))
    assert card["verdict"] == "RESISTED"


def test_assert_resists_reports_each_finding(fixtures):
    with pytest.raises(HackfloorFailure) as info:
        assert_resists(str(fixtures / "rlvr" / "vulnerable_math"))
    message = str(info.value)
    assert "HF-DUMP [critical]" in message
    assert "HF-FORMAT" not in message  # medium, below the default fail_on=high
    assert info.value.card["verdict"] == "VULNERABLE"


def test_fail_on_threshold(fixtures):
    with pytest.raises(HackfloorFailure, match="HF-FORMAT"):
        assert_resists(str(fixtures / "rlvr" / "vulnerable_math"), fail_on="medium")
    card = assert_resists(str(fixtures / "rlvr" / "vulnerable_math"), fail_on="none")
    assert card["verdict"] == "VULNERABLE"
    with pytest.raises(ValueError):
        assert_resists(str(fixtures / "rlvr" / "fixed_math"), fail_on="low")


def test_run_scan_accepts_probe_selection(fixtures):
    card = run_scan(str(fixtures / "rlvr" / "vulnerable_math"), probes=["HF-EMPTY"])
    ran = [p["id"] for p in card["probes"] if p["status"] != "not_applicable"]
    assert ran == ["HF-EMPTY"]


def test_plugin_fixture_and_cards(pytester, fixtures):
    pytester.makepyfile(
        f"""
        import pytest

        @pytest.mark.hackfloor
        def test_fixed(hackfloor):
            card = hackfloor.assert_resists({str(fixtures / "rlvr" / "fixed_math")!r})
            assert card["verdict"] == "RESISTED"

        @pytest.mark.hackfloor
        def test_vulnerable(hackfloor):
            hackfloor.assert_resists({str(fixtures / "rlvr" / "vulnerable_math")!r})
        """
    )
    result = pytester.runpytest("--hackfloor-cards", "cards", "-p", "no:cacheprovider")
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["*hackfloor found 1 reward hack(s)*", "*HF-DUMP [[]critical[]]*"])
    cards = sorted(p.name for p in (pytester.path / "cards").iterdir())
    assert cards == [
        "test_plugin_fixture_and_cards.py_test_fixed.json",
        "test_plugin_fixture_and_cards.py_test_vulnerable.json",
    ]


def test_plugin_is_registered(pytester):
    result = pytester.runpytest("--help")
    result.stdout.fnmatch_lines(["*--hackfloor-cards=DIR*"])
    result = pytester.runpytest("--markers")
    result.stdout.fnmatch_lines(["@pytest.mark.hackfloor:*"])
