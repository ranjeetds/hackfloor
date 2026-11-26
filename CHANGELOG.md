# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- With 5 or more tasks, reproducible hack-passes make a probe critical only when they beat
  chance on their own (one-sided sign test against losses, before the Holm correction).
  Otherwise they are listed as isolated hack-passes with their task ids, and the probe is
  judged on its other tasks (`info` if nothing else is significant). On reasoning-gym this was a fixed probe output that
  happened to be a correct answer on one task out of 100.
- A probe variant whose output gives the reference answer (for example an empty answer slot on
  a task whose answer is empty) is no longer graded on that task, so it can no longer produce a
  false hack-pass. The card counts these as `skipped_same_as_reference`.

### Changed

- The terminal evidence lines keep a space after long variant names.
- Terminal and Markdown reports label probe results as `PASS`, `FAIL` or `WARN` rather than
  using check-mark or ballot-x symbols.
- README tightened (install, quickstart, probe table, integrations, integrity card, CI,
  citation) and pictographic symbols removed from documentation.
- README rewritten for newcomers: a plain-English first line, a two-line example of a
  hackable reward function, a quickstart with real output, and links to the docs instead of
  reference tables.

### Added

- Results page for reasoning-gym 0.1.25 and TRL `accuracy_reward`: method, versions,
  commands, and the `game_of_life_halting` finding (fixed upstream in #561).
- `HF-WRONG`, a plausible wrong answer in the right format: the reference answer with a
  boolean or yes/no flipped, the last number changed (by one below 10, otherwise by a tenth
  of its magnitude), or the next option letter, against an empty answer slot. Only a wrong
  answer that reaches the reference score is a finding; graded credit for a near miss is
  `info` (`Probe.needs_hack_pass`). It is the only probe given the reference completion
  (`Probe.uses_reference`, `ProbeContext.reference`). It feeds `semantic.canary_floor`, which
  is now measured instead of `NOT_MEASURED`. New fixtures `rlvr/vulnerable_halting` and
  `rlvr/fixed_halting`. 15 probes in all.
- Bounded partial credit is reported as `info`, not as a finding: a significant effect with no
  hack-pass whose best exploit reward is at most 10% of the reward range. The bound is set
  with `--partial-credit` (0 disables it). The card gains `summary.partial_credit`,
  `method.partial_credit_bound` and a `partial_credit` list in
  `statistical.adversarial_floor`; the probe status enum gains `info`.
- Docs pages: concepts in plain words (glossary and how a finding is decided), background,
  bundled fixtures and their results, comparison with related tools, and roadmap. The
  supported-targets table is now in the adapters page, and responsible use is in the threat
  model page.

## [0.2.0] - 2026-11-26

First release on PyPI.

### Fixed

- CI: the test job no longer runs `uv venv` after `setup-uv` has already created the
  environment, which failed every test job on the first run.

### Added

- Probes `HF-SKIPTEST`, `HF-LOOKUP`, `HF-ECHO`, `HF-JUDGE`, `HF-ANSWERKEY` and `HF-GITLEAK`
  (14 built in), with vulnerable and fixed judge and leaky fixtures.
- Card checks `statistical.gameability_gap` (point-biserial correlation and AUROC against a
  declared bound) and `semantic.no_solution_leakage`; a reproducible hack-pass is always a
  finding.
- Task directories: optional `setup` command, `instruction` file and a sandbox preview for
  leak probes.
- Adapters for reasoning-gym, Prime Intellect `verifiers` (experimental) and single-step
  OpenEnv environments (experimental); `reasoning-gym:`, `verifiers:` and `subject:` targets;
  package extras for each.
- `--openenv-checks PATH`: the card's RFC 008 checks as OpenEnv `CheckResult` records.
- A composite GitHub Action (`action.yml`) and a pre-commit hook.
- `hackfloor.testing.assert_resists` and a pytest plugin with a `hackfloor` fixture.
- A mkdocs-material documentation site with a GitHub Pages workflow.
- CI jobs for the integrations and the action self-test.
- A release workflow that publishes to TestPyPI and PyPI with Trusted Publishing.

## 0.1.0.dev0 (not released)

### Added

- `hackfloor scan`, `hackfloor probes` and `hackfloor version` commands.
- Probe plugin interface with a registry and the `hackfloor.probes` entry-point group.
- Adapters for plain reward functions (plain, verl and TRL signatures) and for Harbor-style
  task directories described by `hackfloor.toml`.
- Probes `HF-EMPTY`, `HF-FORMAT`, `HF-DUMP`, `HF-EQ`, `HF-EXIT`, `HF-CONFTEST`,
  `HF-TESTEDIT` and `HF-REWARDFILE`, each with matched controls.
- Calibration against the reference solution and the null policy; paired sign test with Holm
  correction, deterministic-replay rule for small task sets, Clopper-Pearson intervals and a
  seeded paired bootstrap.
- Integrity card v0.1 (JSON, with schema) using OpenEnv RFC 008 check ids, a Markdown report
  and a rich terminal view.
- Vulnerable and fixed fixture environments, tests, CI and documentation outline.

[Unreleased]: https://github.com/ranjeetds/hackfloor/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ranjeetds/hackfloor/releases/tag/v0.2.0
