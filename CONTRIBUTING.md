# Contributing to hackfloor

Thanks for helping. hackfloor is only useful if its findings are trustworthy, so the bar for
new probes is evidence, not ideas.

## Setup

```bash
git clone https://github.com/ranjeetds/hackfloor.git
cd hackfloor
uv venv && uv pip install -e ".[dev]"
pre-commit install   # optional: runs ruff on commit
```

Before opening a pull request:

```bash
ruff check .
ruff format --check .
pytest
```

If you change terminal output or the card, regenerate the README images with
`python scripts/render_readme_assets.py` and commit the updated SVGs.

## Adding a probe

A probe pull request needs:

1. **A public reference.** A paper, a blog post, an issue or a commit that documents the hack
   being used or found. Put it in the probe's `references`.
2. **A matched control.** A variant that does the same kind of thing without the exploit
   payload (for example an empty `conftest.py` next to the patched one). Without a control,
   a finding cannot be told apart from noise.
3. **A fixture pair.** A small vulnerable environment the probe hacks and a fixed twin it
   does not, under `fixtures/`, with tests in `tests/`.
4. **The capabilities it needs** in `requires`, so it is skipped on targets it cannot apply to.
5. **The minimal form only.** Keep payloads as small as the published description allows,
   and start every file a probe writes with `CANARY` from `hackfloor.probes.workspace`.

Probe ids are `HF-` plus a short upper-case name. Third-party probes outside this repository
should use their own prefix and register through the `hackfloor.probes` entry point.

## Adding an adapter

An adapter implements the `Subject` protocol in `hackfloor/core.py`: `tasks()`, `gold()`,
`null()`, `grade()`, `capabilities()` and `describe()`. Include a fixture and tests that show
calibration passes on a correct environment.

## Reporting a false positive or a missed hack

Open an issue with the template. Attach the integrity card (`hackfloor-card.json`) and, if
you can, a minimal environment that reproduces it. A missed hack in a public environment
should be reported to that environment's maintainers first; see [SECURITY.md](SECURITY.md).

## Commit style

Small, focused commits with a clear subject line. Sign off your commits (`git commit -s`) to
certify the [Developer Certificate of Origin](https://developercertificate.org/).

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
