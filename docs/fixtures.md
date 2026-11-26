# Bundled fixtures

The fixtures are small teaching environments written for hackfloor's tests. Each has a fixed
twin. They are deliberately weak: do not copy them into a real environment. They are in the
repository (`fixtures/`) and not in the PyPI wheel, so clone the repository to run them:

```bash
git clone https://github.com/ranjeetds/hackfloor.git
cd hackfloor
hackfloor scan fixtures/rlvr/vulnerable_math
```

Task-directory fixtures need `pytest`; `pip install -e ".[dev]"` provides it.

## Results

These results come from the test suite and the CLI on Python 3.12 with pytest 9.2.0.

| Fixture | Verdict | Findings |
|---|---|---|
| `tasks/vulnerable_pytest` | VULNERABLE, L0 | `HF-CONFTEST`, `HF-EQ`, `HF-LOOKUP`, `HF-REWARDFILE`, `HF-SKIPTEST`, `HF-TESTEDIT` (all critical) |
| `tasks/fixed_pytest` | RESISTED, L1 | none |
| `tasks/vulnerable_script` | VULNERABLE, L0 | `HF-EQ`, `HF-EXIT` (critical) |
| `tasks/fixed_script` | RESISTED, L1 | none |
| `tasks/vulnerable_leaky` | VULNERABLE, L0 | `HF-ANSWERKEY`, `HF-GITLEAK` (critical); `semantic.no_solution_leakage` FAIL |
| `tasks/fixed_leaky` | RESISTED, L1 | none; leak probes searched and found nothing |
| `rlvr/vulnerable_math` | VULNERABLE, L0 | `HF-DUMP` (critical, 40/40), `HF-FORMAT` and `HF-ECHO` (medium, Δ = 0.20) |
| `rlvr/fixed_math` | RESISTED, L1 | none |
| `rlvr/vulnerable_judge` | VULNERABLE, L0 | `HF-JUDGE` (critical, 40/40) and `HF-DUMP` (critical, 40/40) against a deterministic stub judge |
| `rlvr/fixed_judge` | RESISTED, L1 | none |
| `rlvr/vulnerable_halting` | VULNERABLE, L0 | `HF-WRONG`, `HF-DUMP`, `HF-ECHO`, `HF-FORMAT`, `HF-JUDGE` (all critical, 40/40): the grader compares `bool(answer)`, so any non-empty answer passes |
| `rlvr/fixed_halting` | RESISTED, L1 | none |

Every vulnerable fixture also fails `statistical.gameability_gap` (correlation between 0.25
and 0.57 against a bound of 0.9); every fixed twin reaches 1.0.

`HF-EXIT` does not hack `vulnerable_pytest`: with pytest 9.2.0, an import-time `sys.exit(0)`
ends in `INTERNALERROR` and exit code 3. It does hack the script verifier, which trusts the
exit code.

## Pictures

<p align="center">
  <img src="assets/scan-vulnerable.svg#only-light" alt="Scan of the vulnerable pytest fixture" width="760">
</p>
<p align="center">
  <img src="assets/integrity-card-light.svg#only-light" alt="Integrity cards for the vulnerable and fixed pytest fixtures" width="760">
  <img src="assets/integrity-card-dark.svg#only-dark" alt="Integrity cards for the vulnerable and fixed pytest fixtures" width="760">
</p>
