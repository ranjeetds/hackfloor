# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.2] - 2026-11-27

### Fixed

- Scans of more than about 1,000 tasks crashed with `OverflowError` at the end of the run.
  The exact binomial sums multiplied huge integers by floats. The binomial tails and the
  Clopper-Pearson interval now use the regularised incomplete beta function in log space, the
  AUROC is computed from ranks, and the bootstrap's work is bounded for large task sets. Results
  up to 1,000 tasks are unchanged; a 20,000-row scan of a simple reward function went from
  about 8.5 minutes to about 15 seconds.
- A reward function that raised on probe outputs (for example `int(completion)`) was reported
  `RESISTED` with exit code 0, because every failed attempt scored the floor and looked like
  resistance. A probe whose attempts mostly failed (an error, or a reward outside the declared
  range) is now not evaluated (status `error`), and a scan with no findings and such a probe is
  `INCONCLUSIVE` (exit code 2, level L0). `statistical.adversarial_floor` is `NOT_MEASURED`
  then. Findings are kept. The terminal prints how many grader calls failed and the first
  error, the `--quiet` line gains `grader_errors=N`, and the card records the counts per probe.
- Error messages, output paths and the `probes` listing no longer pass through rich markup, so
  text in square brackets (for example the `hackfloor[reasoning-gym]` install hint) is shown
  instead of being swallowed, and a path such as `x[/y].py` no longer crashes the CLI.
- The HF-WRONG row on the Probes page was cut off from its table by a blank line, and the
  README said eight more probes instead of nine. Tests now guard both.

### Added

- The `INCONCLUSIVE` verdict (also in the card schema, the Action's `verdict` output and
  `assert_resists`, which fails on it like on `UNCALIBRATED`).

### Changed

- Terminal output no longer uses green or cyan: `PASS` is bold, `INFO` and the header are
  blue, and the `RESISTED` badge is blue; failures stay red.
- Cleaner README and docs: a centred header, one real scan image, and a neutral palette
  (white or near-black, greys, one indigo accent, muted red for failures) in the docs theme.
- README and docs images are now PNGs rendered from real scans by
  `scripts/render_readme_assets.py`, in light and dark variants.

## [0.2.1] - 2026-11-26

### Added

- `HF-WRONG`, a plausible wrong answer in the right format: the reference answer with a
  boolean or yes/no flipped, the last number changed (by one below 10, otherwise by a tenth
  of its magnitude), or the next option letter, against an empty answer slot. Only a wrong
  answer that reaches the reference score is a finding; graded credit for a near miss is
  `info` (`Probe.needs_hack_pass`). It is the only probe given the reference completion
  (`Probe.uses_reference`, `ProbeContext.reference`). It feeds `semantic.canary_floor`, which
  is now measured instead of `NOT_MEASURED`. New fixtures `rlvr/vulnerable_halting` and
  `rlvr/fixed_halting`. 15 probes in all.
- A new probe status, `info`, for results that are not findings and do not change the
  verdict: bounded partial credit, near-miss credit from `HF-WRONG`, and isolated
  hack-passes. Bounded partial credit is a significant effect with no hack-pass whose best
  exploit reward is at most 10% of the reward range; set the bound with `--partial-credit`
  (0 disables it). The card gains `summary.partial_credit`, `method.partial_credit_bound` and
  a `partial_credit` list in `statistical.adversarial_floor`.
- Results page for reasoning-gym 0.1.25 and TRL `accuracy_reward`: method, versions,
  commands, and the `game_of_life_halting` finding (fixed upstream in #561).
- Docs pages: concepts in plain words (glossary and how a finding is decided), background,
  bundled fixtures and their results, and roadmap. The supported-targets table is now in the
  adapters page, and responsible use is in the threat model page.

### Changed

- With 5 or more tasks, reproducible hack-passes make a probe critical only when they beat
  chance on their own (one-sided sign test against losses, before the Holm correction).
  Otherwise they are listed as isolated hack-passes with their task ids, and the probe is
  judged on its other tasks. On reasoning-gym these were fixed probe outputs that happened
  to be a correct answer on one task out of 100.
- `hackfloor scan --quiet` also prints `partial_credit=N`.
- Terminal and Markdown reports label probe results as `PASS`, `FAIL`, `INFO` or `WARN`
  rather than using check-mark or ballot-x symbols.
- The comparison page is rewritten: which tool to pick for which input, envdoctor, rlgate,
  gradecheck, nudi, BenchJack and OpenEnv side by side, where other tools are ahead, and the
  paid audits (Holdout, Cupel).
- README rewritten for newcomers: a plain-English first line, a two-line example of a
  hackable reward function, a quickstart with real output, real-world results, and links to
  the docs instead of reference tables. Pictographic symbols removed from documentation.
- The GitHub Action and pre-commit examples pin `v0.2.1`.

### Fixed

- A probe variant whose output gives the reference answer (for example an empty answer slot
  on a task whose answer is empty) is no longer graded on that task, so it can no longer
  produce a false hack-pass. The card counts these as `skipped_same_as_reference`.
- The terminal evidence lines keep a space after long variant names.

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

[Unreleased]: https://github.com/ranjeetds/hackfloor/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/ranjeetds/hackfloor/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/ranjeetds/hackfloor/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ranjeetds/hackfloor/releases/tag/v0.2.0
