# Quickstart

## Install

hackfloor is not on PyPI yet.

```bash
git clone https://github.com/ranjeetds/hackfloor.git
cd hackfloor
uv venv && uv pip install -e ".[dev]"
```

## First scan

```bash
hackfloor scan fixtures/tasks/vulnerable_pytest --report report.md
```

The scan:

1. runs the reference solution and the null policy (an untouched workspace) to calibrate;
2. runs every probe that applies to the target, each with a matched control, twice;
3. prints a table, writes `hackfloor-card.json`, and writes `report.md`.

## Reading the result

| Column | Meaning |
|---|---|
| result | `HACK` (a finding), `resisted`, `flaky` (did not reproduce on every replay) |
| severity | `critical`: reached the reference score on at least one task; `high`: mean gap at least half the reference-to-null gap; `medium`: smaller but significant |
| Δ floor | mean reward of the exploit minus its matched control |
| hack-pass | tasks where the exploit reached the reference score |

The verdict is `VULNERABLE` (critical or high finding), `WEAK` (only medium findings),
`RESISTED` (no findings) or `UNCALIBRATED` (the reference does not beat the null policy, so
nothing can be concluded).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | no finding at or above `--fail-on` (default `high`) |
| 1 | at least one finding at or above `--fail-on` |
| 2 | uncalibrated, or the target could not be loaded |

## Useful options

```text
--probes HF-EQ,HF-CONFTEST   run only these probes
--tasks 50                   use the first 50 rows or tasks
--replays 3                  replay every attempt three times
--fail-on critical|high|medium|none
--quiet                      print only the verdict line
```
