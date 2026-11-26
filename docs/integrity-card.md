# Integrity card

Every scan writes a JSON card (default `hackfloor-card.json`) that validates against
[`card-0.1.schema.json`](https://github.com/ranjeetds/hackfloor/blob/main/src/hackfloor/schema/card-0.1.schema.json).

## Top-level fields

| Field | Meaning |
|---|---|
| `verdict` | `VULNERABLE`, `WEAK`, `RESISTED` or `UNCALIBRATED` |
| `level` | integrity level, or `null` when uncalibrated |
| `subject` | what was scanned: framework, name, data or task paths, reward range |
| `calibration` | reference and null-policy means, replay consistency |
| `probes` | one entry per probe: status, severity, floor gap with CI, hack-pass count with CI, paired wins and losses, decision basis, evidence |
| `checks` | check results keyed by id |
| `method` | replays, alpha, minimum floor gap, seed, a hash of the probe set |
| `reproduce` | the command that produced the card |

## Check ids

Ids follow OpenEnv's RFC 008 validation code (openenv/OpenEnv v0.14), plus one
hackfloor-specific id.

| Id | What hackfloor measures |
|---|---|
| `hackfloor.calibration` | the reference beats the null policy on every task, consistently across replays |
| `semantic.oracle_max` | every reference run reaches the declared maximum (tolerance 0) |
| `semantic.floor_gap` | the highest null-policy reward sits at least `min_floor_gap` of the range below the maximum and below the lowest reference reward |
| `statistical.adversarial_floor` | no probe in the panel has a finding; when none does, the 95% upper bound on the hack-pass rate per probe and task |
| `statistical.gameability_gap` | point-biserial correlation and AUROC between solved and reward across all scripted attempts, against a declared bound (see [Statistics](statistics.md#gameability)) |
| `semantic.no_solution_leakage` | no leak probe reaches a reference solution, and the reference answer is not visible in the prompt; `NOT_MEASURED` when there is nothing to check |
| `runtime.reward_well_formed` | every reward is finite and inside the declared range, and no grader call failed |
| `runtime.oracle_containment` | partial: only the reward-file write probe; `SKIP` when it does not apply |
| `semantic.canary_floor` | `NOT_MEASURED` |
| `runtime.network_policy`, `runtime.host_containment`, `runtime.resource_bounds`, `runtime.episode_isolation` | `NOT_MEASURED` (need container isolation or multi-episode runs) |

`statistical.adversarial_floor` and `statistical.gameability_gap` are in the lane RFC 008
reserves for operators; hackfloor is one way to produce them. `hackfloor scan --openenv-checks
PATH` writes these checks as OpenEnv `CheckResult` records (see [Adapters](adapters.md#openenv-check-results)).

`NOT_MEASURED` is never a pass.

## Levels

| Level | Rule | Available |
|---|---|---|
| L0 | any critical or high finding, or any malformed reward | since v0.1 |
| L1 | calibrated, and no critical or high finding | since v0.1 |
| L2 | L1, plus a bounded gameability gap and passing containment checks | planned |
| L3 | L2, plus the canary suite and an independent replay | planned |
