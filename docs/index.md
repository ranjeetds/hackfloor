---
hide:
  - navigation
---

# hackfloor

<p align="center">
  <img src="assets/banner-light.svg#only-light" alt="hackfloor" width="720">
  <img src="assets/banner-dark.svg#only-dark" alt="hackfloor" width="720">
</p>

**Prove that agents which don't solve the task can't score.** hackfloor runs adversarial
probes against an RL environment's grader or an agent benchmark: cheap, known reward hacks,
each with a matched control. It reports paired statistics and writes an integrity card that
anyone can re-check.

```bash
hackfloor scan fixtures/tasks/vulnerable_pytest --report report.md
```

<p align="center">
  <img src="assets/scan-vulnerable.svg" alt="A scan of a vulnerable task" width="760">
</p>

| Page | What it covers |
|---|---|
| [Quickstart](quickstart.md) | install, first scan, reading the output |
| [Adapters](adapters.md) | reward functions, task directories, reasoning-gym, verifiers, OpenEnv |
| [CI](ci.md) | the GitHub Action, the pre-commit hook and the pytest plugin |
| [Probes](probes.md) | every built-in probe, its control, and what is not covered yet |
| [Integrity card](integrity-card.md) | the JSON format, check ids, levels |
| [Statistics](statistics.md) | calibration, decisions, severity, gameability |
| [Threat model](threat-model.md) | what hackfloor does and does not protect against |
