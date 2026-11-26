"""pytest plugin: a ``hackfloor`` fixture for asserting that a grader resists reward hacks.

Registered through the ``pytest11`` entry point, so it loads wherever hackfloor is installed,
including pytest runs started by graders under test. It therefore only registers an option, a
marker and a fixture, and imports nothing heavy until the fixture is used.

    def test_my_grader_resists(hackfloor):
        hackfloor.assert_resists("envs/my_task")

``--hackfloor-cards DIR`` keeps each scan's integrity card as ``DIR/<test id>.json``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("hackfloor")
    group.addoption(
        "--hackfloor-cards",
        metavar="DIR",
        default=None,
        help="write the integrity card of every hackfloor scan in a test to DIR",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "hackfloor: a test that runs a hackfloor scan (select with -m hackfloor)"
    )


class HackfloorHelper:
    """What the ``hackfloor`` fixture returns."""

    def __init__(self, node_id: str, cards_dir: str | None) -> None:
        self._node_id = node_id
        self._cards_dir = Path(cards_dir) if cards_dir else None
        self.cards: list[dict[str, Any]] = []

    def _keep(self, card: dict[str, Any]) -> None:
        self.cards.append(card)
        if self._cards_dir is not None:
            self._cards_dir.mkdir(parents=True, exist_ok=True)
            stem = re.sub(r"[^\w.-]+", "_", self._node_id).strip("_")
            suffix = f"-{len(self.cards)}" if len(self.cards) > 1 else ""
            path = self._cards_dir / f"{stem}{suffix}.json"
            path.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")

    def scan(self, target: Any, **kwargs: Any) -> dict[str, Any]:
        """Run a scan and return the integrity card, without asserting anything."""
        from hackfloor.testing import run_scan

        card = run_scan(target, **kwargs)
        self._keep(card)
        return card

    def assert_resists(self, target: Any, **kwargs: Any) -> dict[str, Any]:
        """Scan and fail the test on a finding at or above ``fail_on`` (default ``high``)."""
        from hackfloor.testing import HackfloorFailure, assert_resists

        try:
            card = assert_resists(target, **kwargs)
        except HackfloorFailure as failure:
            self._keep(failure.card)
            raise
        self._keep(card)
        return card


@pytest.fixture
def hackfloor(request: pytest.FixtureRequest) -> HackfloorHelper:
    """Scan environments from a test: ``hackfloor.assert_resists(target)``."""
    return HackfloorHelper(request.node.nodeid, request.config.getoption("--hackfloor-cards"))
