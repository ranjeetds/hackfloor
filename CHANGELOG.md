# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
