# How hackfloor compares

Several tools now look for reward hacks before training. They differ mostly in what they
take as input and how they decide that something is a hack. This page says where each one
fits, including where another tool is the better choice.

A "yes" means the project's own README or docs say so, checked on 26 November 2026. A blank
means it is not documented there, not that it is impossible. Versions are the latest
release on that date.

## Pick by what you have

| You have | Look at |
|---|---|
| A reward function for completions (verl, TRL, a reasoning-gym dataset) | hackfloor, envdoctor |
| A Prime Intellect `verifiers` environment | envdoctor, gradecheck, hackfloor (experimental) |
| An Inspect AI task | envdoctor |
| Harbor, Terminal-Bench, SWE-bench or MiMo task directories, run in Docker | rlgate, nudi |
| A task directory with a grade command, run locally | hackfloor, gradecheck |
| A whole benchmark repository to audit, with an LLM | BenchJack |
| An OpenEnv environment | OpenEnv's own validation, plus hackfloor's check export |
| Budget for an outside audit | Holdout, Cupel (paid services) |

## Open-source tools

| | [hackfloor](https://github.com/ranjeetds/hackfloor) 0.2.2 | [envdoctor](https://github.com/meagoodboy/envdoctor) 0.1.0 | [rlgate](https://github.com/deepak-foundryai/rlgate) 1.0.0 | [gradecheck](https://github.com/PoorvaJ-WW/gradecheck) 0.1.0 | [nudi](https://github.com/standardnormal-ai/nudi) 0.6.0 | [BenchJack](https://github.com/benchjack/benchjack) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| How it finds hacks | 15 scripted probes | scripted policies and 13 checks | 76 rules in 6 steps | 5 scripted attacks | LLM agent swarms | static analysis plus an LLM agent |
| Needs an LLM or API key | no | no | no (optional `--deep-review`) | no | yes | yes |
| Completion reward functions | yes | yes | | | | |
| `verifiers` environments | experimental | yes | | yes | planned | |
| Task directories | yes, local subprocess | | yes (Harbor, TB, SWE-bench, MiMo) | yes | yes (Harbor) | benchmark repos |
| Container sandbox | planned (v0.3) | | yes (Docker, Daytona) | | yes (Modal) | partial (marked work in progress) |
| Reference and do-nothing calibration | yes | yes | yes (5 runs each) | yes (noop baseline) | | |
| Wrong-answer check (a perturbed correct answer) | yes (`HF-WRONG`) | yes (`grader_accepts_wrong`) | | | | |
| Workspace tampering (always-equal, `sys.exit`, `conftest.py`, edited tests) | yes | | yes | partial (test deletion) | yes (agent-found) | yes |
| Matched control per exploit, paired sign test with Holm correction | yes | | | | | |
| Error rates over simulated training runs | | | | | yes | |
| Published audit of a public collection | [reasoning-gym 0.1.25](results/reasoning-gym.md), 100 datasets | Prime Intellect Hub, 149 sampled | | | Terminal-Bench 4.0.0, 4 tasks | 8 agent benchmarks |
| Output | JSON card with schema, Markdown, OpenEnv `CheckResult` | JSON, SARIF | HTML, Markdown, JSON, SARIF, badge | JSON | reports for coding agents | web dashboard, PoC code |
| Works as a CI gate | yes (Action, pre-commit, pytest plugin) | yes (exit code, pytest plugin) | yes (Action, pre-commit) | yes (exit code) | | |
| Uses OpenEnv RFC 008 check ids | yes | | | | | |

### Where other tools are ahead

- **envdoctor** is the closest tool to hackfloor's completion probes and covers more ground
  there. It reads the answer format from the prompt instead of asking for a gold template,
  supports Inspect AI tasks, and has published an audit of 87 environments from the Prime
  Intellect Hub, with every finding re-checked and its own false positives listed. If you
  only grade completions, try it.
- **rlgate** goes much deeper on coding tasks: real Docker or Daytona builds, mutation of
  the reference fix, leaked patch files, fairness checks, SARIF output and a reproduce
  command for each proven finding. hackfloor's workspace probes run as local subprocesses,
  which is not a security boundary.
- **nudi** and **BenchJack** use LLM agents, so they can find flaws nobody has written a
  probe for. A scripted tool, hackfloor included, only finds the hacks it knows.

### Where hackfloor differs

- **Matched controls and paired statistics.** Every exploit is compared with a control
  that does the same thing without the exploit, on the same task. Findings need an exact
  sign test with Holm correction across probes, or a hack that reproduces on every replay.
  A format bonus therefore shows up as a format bonus, not as a broken grader, and bounded
  partial credit is reported as `INFO` rather than as a finding. See
  [Statistics](statistics.md).
- **One panel for both kinds of grader.** The same scan, card and CI gate work for a
  completion reward function and for a task directory with tests.
- **OpenEnv RFC 008 ids.** The integrity card uses the check ids from OpenEnv's validation
  proposal and can be exported as OpenEnv `CheckResult` records (see
  [Background](background.md)).

## OpenEnv validation

[OpenEnv](https://github.com/openenv/OpenEnv) 0.15.0 grades Harbor tasks for
`semantic.oracle_max`, `semantic.floor_gap` and author-supplied canaries
(`semantic.canary_floor`). `statistical.adversarial_floor`, the panel of non-solving
policies, is defined in [RFC 008](https://github.com/openenv/OpenEnv/issues/778) but has
no grader yet. hackfloor is meant to be a panel OpenEnv can use, not a replacement for its
validator.

## Paid audits

- [Holdout](https://holdout.cc/audits) audits RL environments as a service and publishes
  some findings in [holdout-findings](https://github.com/holdout-cc/holdout-findings), for
  example an early `raise SystemExit(0)` that passes NeMo Gym's SciCode grader.
- [Cupel](https://inductive.ml/cupel) is the paid audit service of Inductive ML. It lists,
  for example, a working-directory write that forces a pass from the MiMo grader on 1,322
  of 2,601 environments.

An audit by people who read your grader will find things no scanner does. A scanner is
cheaper to run on every change.

## Research

- [BenchJack](https://arxiv.org/abs/2605.12673) (arXiv 2605.12673) catalogues eight classes
  of benchmark flaws and found exploits in every one of the agent benchmarks it audited.
- [ImpossibleBench](https://github.com/safety-research/impossiblebench) and
  [EvilGenie](https://arxiv.org/abs/2511.21654) measure how often models take such
  shortcuts when they are available.
