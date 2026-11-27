"""Adapters against the real frameworks. Each test skips when its package is missing.

Install with ``pip install -e ".[dev,integrations]"`` (verifiers needs Python 3.11+).
"""

import json
import os
import sys
from importlib import resources

import pytest

from hackfloor import scan
from hackfloor.adapters import resolve_subject
from hackfloor.card import build_card
from hackfloor.export import openenv_check_results
from hackfloor.scan import ScanConfig


@pytest.fixture
def integration_fixtures(fixtures, monkeypatch):
    monkeypatch.syspath_prepend(str(fixtures / "integrations"))
    yield
    for name in ("verifiers_tasks", "openenv_env"):
        sys.modules.pop(name, None)


def _probes(result):
    return {p.probe.id: p.status for p in result.probes if p.status != "not_applicable"}


def test_reasoning_gym_dataset_calibrates_and_resists_task_blind_probes():
    pytest.importorskip("reasoning_gym")
    subject = resolve_subject("reasoning-gym:basic_arithmetic", limit=8, seed=0)
    assert subject.framework == "reasoning-gym"
    assert len(subject.tasks()) == 8
    task = subject.tasks()[0]
    assert subject.gold(task).startswith("<answer>")
    assert subject.grade(task, subject.gold(task)).reward == 1.0
    assert subject.grade(task, "").reward == 0.0
    result = scan(subject, ScanConfig(replays=1))
    assert result.calibration.sanity == "PASS"
    assert result.verdict == "RESISTED"


@pytest.mark.parametrize(
    ("factory", "verdict"), [("vulnerable", "VULNERABLE"), ("fixed", "RESISTED")]
)
def test_verifiers_taskset(integration_fixtures, factory, verdict):
    pytest.importorskip("verifiers.v1")
    subject = resolve_subject(
        f"verifiers:verifiers_tasks:{factory}", gold_template="<answer>{answer}</answer>"
    )
    assert subject.framework == "verifiers"
    task = subject.tasks()[0]
    assert subject.grade(task, subject.gold(task)).reward == 1.0
    result = scan(subject, ScanConfig(replays=1))
    assert result.calibration.sanity == "PASS"
    assert result.verdict == verdict
    assert _probes(result)["HF-DUMP"] == ("finding" if factory == "vulnerable" else "resisted")


@pytest.mark.parametrize(
    ("factory", "verdict"), [("vulnerable", "VULNERABLE"), ("fixed", "RESISTED")]
)
def test_openenv_environment(integration_fixtures, factory, verdict):
    pytest.importorskip("openenv.core.env_server.interfaces")
    subject = resolve_subject(f"subject:openenv_env:{factory}")
    result = scan(subject, ScanConfig(replays=1))
    assert result.calibration.sanity == "PASS"
    assert result.verdict == verdict


def test_check_results_validate_against_openenv(integration_fixtures):
    pytest.importorskip("openenv.validation.report")
    jsonschema = pytest.importorskip("jsonschema")
    from openenv.validation.report import CheckResult

    card = build_card(
        scan(resolve_subject("subject:openenv_env:vulnerable"), ScanConfig(replays=1))
    )
    schema = json.loads(
        resources.files("openenv.validation").joinpath("schemas/report-v2.schema.json").read_text()
    )
    check_schema = {"$defs": schema["$defs"], **schema["$defs"]["CheckResult"]}
    results = openenv_check_results(card)
    for record in results:
        jsonschema.validate(record, check_schema)
        CheckResult.model_validate(record)
    by_id = {r["check_id"]: r["status"] for r in results}
    assert by_id["statistical.adversarial_floor"] == "fail"


@pytest.mark.skipif(
    not os.environ.get("HACKFLOOR_OPENENV_REPO"),
    reason="set HACKFLOOR_OPENENV_REPO to an openenv/OpenEnv checkout",
)
def test_upstream_reasoning_gym_env(monkeypatch):
    """OpenEnv's own envs/reasoning_gym_env, driven through OpenEnvSubject."""
    pytest.importorskip("reasoning_gym")
    monkeypatch.syspath_prepend(os.path.join(os.environ["HACKFLOOR_OPENENV_REPO"], "envs"))
    from reasoning_gym_env.models import ReasoningGymAction
    from reasoning_gym_env.server.reasoning_gym_environment import ReasoningGymEnvironment

    from hackfloor.adapters import OpenEnvSubject

    subject = OpenEnvSubject(
        ReasoningGymEnvironment,
        [
            {"dataset_name": "basic_arithmetic", "dataset_config": {}, "seed": i, "size": 1}
            for i in range(6)
        ],
        make_action=lambda text: ReasoningGymAction(answer=text),
        gold=lambda env, obs, kwargs: env._current_entry["answer"],
    )
    result = scan(subject, ScanConfig(replays=1))
    assert result.calibration.sanity == "PASS"


@pytest.mark.parametrize(
    ("factory", "verdict"),
    [
        ("multistep_vulnerable", "VULNERABLE"),
        ("multistep_fixed", "RESISTED"),
    ],
)
def test_openenv_multistep_environment(integration_fixtures, factory, verdict):
    pytest.importorskip("openenv.core.env_server.interfaces")
    subject = resolve_subject(f"subject:openenv_env:{factory}")
    result = scan(subject, ScanConfig(replays=1))
    assert result.calibration.sanity == "PASS"
    assert result.verdict == verdict
