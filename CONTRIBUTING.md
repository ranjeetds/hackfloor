# Contributing to hackfloor

Thanks for helping. hackfloor is only useful if its findings are trustworthy, so the bar for
new probes is evidence, not ideas. Good places to start are the issues labelled
[`good first issue`](https://github.com/ranjeetds/hackfloor/labels/good%20first%20issue) and
[`help wanted`](https://github.com/ranjeetds/hackfloor/labels/help%20wanted).

## Development setup

hackfloor uses [uv](https://docs.astral.sh/uv/). Python 3.10 to 3.13 are supported.

```bash
git clone https://github.com/<you>/hackfloor.git
cd hackfloor
uv venv                              # creates .venv
uv pip install -e ".[dev]"           # hackfloor, pytest, ruff, jsonschema
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pre-commit install                   # optional: ruff on every commit (pip install pre-commit)
```

Optional extras:

```bash
uv pip install -e ".[integrations]"  # reasoning-gym, verifiers (3.11+), openenv
uv pip install -e ".[docs]"          # mkdocs-material, for the docs site
```

Before opening a pull request:

```bash
ruff check .
ruff format --check .
pytest                               # integration tests skip unless the extras are installed
mkdocs build --strict                # if you changed docs/ (needs the docs extra)
```

If you change terminal output or the card, regenerate the README images with
`python scripts/render_readme_assets.py` and commit the updated SVGs.

## Project layout

| Path | What lives there |
|---|---|
| `src/hackfloor/core.py` | `Subject` protocol, `TaskRef`, `Workspace`, `Attempt`, capabilities |
| `src/hackfloor/probes/` | probes: `completion.py`, `workspace.py`, `leak.py`; `base.py` has the plugin API |
| `src/hackfloor/adapters/` | turn an environment into a `Subject` |
| `src/hackfloor/scan.py`, `stats.py` | calibration, paired decisions, severity |
| `src/hackfloor/card.py`, `export.py` | the integrity card and the OpenEnv `CheckResult` export |
| `fixtures/` | small vulnerable environments and their fixed twins |
| `tests/` | pytest suite; `test_integrations.py` uses the real frameworks |
| `docs/` | the documentation site |

## Writing a probe

A probe is a frozen dataclass that yields **variants**. Each variant is an exploit plus a
matched control: the same kind of action without the exploit payload. hackfloor grades both
with the real grader and only reports a finding when the exploit beats its control.

```python
from dataclasses import dataclass, field

from hackfloor.core import Capability
from hackfloor.probes.base import Probe, ProbeContext, Variant, register


@register
@dataclass(frozen=True)
class RepeatedSlotProbe(Probe):
    id: str = "HF-REPEAT"
    family: str = "form"
    title: str = "Many answer slots"
    mechanism: str = "Emits the answer slot many times with different guesses."
    requires: frozenset[Capability] = field(
        default_factory=lambda: frozenset({Capability.COMPLETION})
    )
    references: tuple[str, ...] = ("Link to where this hack is documented",)

    def variants(self, ctx: ProbeContext) -> list[Variant]:
        guesses = "".join(ctx.wrap(str(n)) for n in range(10))
        # Control: the same scaffolding with empty slots, so a format bonus cancels out.
        return [Variant("ten-slots", guesses, control=ctx.wrap("") * 10)]
```

- **Completion probes** return strings. They never see the reference answer: only
  `ctx.gold_template` (via `ctx.wrap`) and the prompt (`ctx.observation`). The one
  exception is a probe that sets `uses_reference = True` (like `HF-WRONG`), which receives
  the reference completion as `ctx.reference` in order to make it wrong.
- **Workspace probes** return functions that edit a `Workspace` (`ws.write`, `ws.delete`,
  `ws.entry_file`, `ws.entry_functions`, `ws.visible_tests()`); see `probes/workspace.py`.
- `requires` lists the capabilities the probe needs, so it is skipped where it cannot apply.
- Return `[]` when there is nothing to try on a task.
- Start every file a probe writes with `CANARY` from `hackfloor.probes.workspace`.

Try it from Python once the module defining it has been imported (built-in probes are
imported in `probes/__init__.py`, after which `hackfloor scan --probes HF-REPEAT` works too):

```python
from hackfloor import scan
from hackfloor.adapters import resolve_subject
from hackfloor.scan import ScanConfig

result = scan(resolve_subject("fixtures/rlvr/vulnerable_math"), ScanConfig(probe_ids=["HF-REPEAT"]))
print([(p.probe.id, p.status) for p in result.probes])
```

A probe pull request needs:

1. **A public reference.** A paper, blog post, issue or commit that documents the hack being
   used or found. Put it in `references`.
2. **A matched control.** Without one, a finding cannot be told apart from noise.
3. **A fixture pair.** A small vulnerable environment the probe hacks and a fixed twin it does
   not, under `fixtures/`, with tests in `tests/` (see `tests/test_taskdir.py` and
   `tests/test_rlvr.py` for the pattern).
4. **The minimal form only.** Keep payloads as small as the published description allows.
5. **Docs.** A row in `docs/probes.md` and in the README probe table, and the id added to
   `tests/test_registry.py`.

Probe ids are `HF-` plus a short upper-case name. Probes published outside this repository
should use their own prefix and register through the `hackfloor.probes` entry point:

```toml
[project.entry-points."hackfloor.probes"]
myprobes = "my_package.probes:PROBES"   # a list of Probe instances
```

## Writing an adapter

An adapter implements the `Subject` protocol in `src/hackfloor/core.py`: `tasks()`, `gold()`,
`null()`, `grade()`, `capabilities()` and `describe()`. If the environment grades one
completion per task, subclass `CompletionSubject` in `adapters/base.py` and implement
`tasks()`, `reference()`, `prompt()` and `score()`. Always call the framework's own grader.

Include a vulnerable and a fixed example and tests that show calibration passes. Adapters for
optional frameworks import lazily, get an extra in `pyproject.toml`, and have tests in
`tests/test_integrations.py` that skip when the framework is missing.

## Reporting a false positive or a missed hack

Open an issue with the matching template. Attach the integrity card (`hackfloor-card.json`)
and, if you can, a minimal environment that reproduces it. A hack in someone else's public
environment should be reported to its maintainers privately first; see
[SECURITY.md](SECURITY.md).

## Sign-off (DCO)

Every commit must be signed off to certify the
[Developer Certificate of Origin](https://developercertificate.org/): that you wrote the
change or have the right to submit it under the project's license.

```bash
git commit -s -m "probes: add HF-REPEAT"
```

This adds a `Signed-off-by: Your Name <you@example.com>` line that matches your git
`user.name` and `user.email`. A CI check fails pull requests with unsigned commits. To fix
them: `git rebase --signoff main` and force-push your branch.

## Commit and pull request style

Small, focused commits with a subject like `area: what changed` (`probes:`, `adapters:`,
`docs:`, `ci:`). One topic per pull request; fill in the template checklist.

## Recognising contributors

We use [all-contributors](https://allcontributors.org/) to credit code, docs, probes, ideas,
bug reports and reviews. After your first contribution is merged, a maintainer adds you to
the README, or you can comment on your pull request:
`@all-contributors please add @<you> for code` (once the all-contributors app is installed).

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
