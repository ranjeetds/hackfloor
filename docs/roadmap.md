# Roadmap

- [x] **v0.1 foundation:** CLI, probe plugin API, two adapters, 8 probes, matched controls,
  paired statistics, integrity card with schema, Markdown report, fixtures with fixed twins
- [x] **v0.2.0** (first PyPI release): reasoning-gym adapter, experimental `verifiers` and
  OpenEnv adapters, OpenEnv check export, leak and judge probes (14 in all), gameability and
  leakage checks, GitHub Action, pre-commit hook, pytest plugin, docs site
- [x] **v0.2.1**: no grading of probe outputs that give the reference answer, bounded partial
  credit reported as `INFO`, the `HF-WRONG` wrong-answer probe and `semantic.canary_floor`
  (15 probes), [reasoning-gym results](results/reasoning-gym.md)
- [x] **v0.2.2**: statistics that stay finite and fast above 1,000 tasks, `INCONCLUSIVE` when the
  grader errors on most probe attempts, error messages printed verbatim, docs fixes
- [ ] **v0.2.x** (Feb 2027): stable `verifiers` and OpenEnv adapters, multi-step OpenEnv
- [ ] **v0.3** (Apr 2027): container isolation with network, timing and containment probes;
  model-based policies and a gameability gap over trained policies; judge probes against real
  LLM judges; integrity level L2
- [ ] **v1.0** (Jun 2027): 31 probes, canary suite, replayable cards, integrity level L3
- [x] **reasoning-gym 0.1.25:** every dataset scanned; one real finding, already fixed
  upstream. See [Results](results/reasoning-gym.md).
- [ ] **Hub audit (upcoming):** scan public RL environments on the Hugging Face Hub and
  report findings privately to maintainers first.

Also planned: OpenRLHF and inspect_ai scorers, multi-step and HTTP OpenEnv, and native
`task.toml` reading for Harbor tasks.

Ideas and requests are tracked in
[GitHub issues](https://github.com/ranjeetds/hackfloor/issues).
