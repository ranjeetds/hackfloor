# Running hackfloor in CI

## GitHub Action

```yaml
# .github/workflows/hackfloor.yml
name: hackfloor
on: [pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - id: hackfloor
        uses: ranjeetds/hackfloor@main  # pin to a release tag or commit once one exists
        with:
          target: envs/my_task
          args: --replays 3
          install: -r requirements.txt
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: hackfloor-card
          path: hackfloor-card.json
```

The action installs the hackfloor version it is pinned to, runs `hackfloor scan`, and appends
the Markdown report to the job summary. The step fails when a finding is at least as severe as
`fail-on`, and also when the scan is uncalibrated.

| Input | Default | Meaning |
|---|---|---|
| `target` | (required) | what to scan, as for `hackfloor scan` |
| `args` | | extra `hackfloor scan` arguments |
| `fail-on` | `high` | `critical`, `high`, `medium` or `none` |
| `card` | `hackfloor-card.json` | where to write the integrity card |
| `python-version` | `3.12` | set up with `actions/setup-python`; empty uses the `python` on `PATH` |
| `install` | | extra pip requirements the environment under test needs (its grader's tools, e.g. `pytest`) |

Outputs: `verdict`, `level`, `findings` and `card`, set even when the step fails, so a later
step can read them with `if: always()`.

The grader runs on the runner, so install whatever it needs with `install`. A grader that
cannot run makes the reference solution fail, and the scan reports `UNCALIBRATED` instead of a
verdict.

## pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/ranjeetds/hackfloor
    rev: main  # pin to a release tag or commit once one exists
    hooks:
      - id: hackfloor
        args: [envs/my_task, --quiet, --replays, "1", --out, .hackfloor/card.json]
        files: ^envs/my_task/
```

The hook takes no file names; the target and options go in `args`. Set `files` so it runs only
when the environment changes. pre-commit fails a hook that leaves new files behind, so list the
card directory and `__pycache__/` in `.gitignore`.
