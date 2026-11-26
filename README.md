<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/banner-light.svg">
    <img alt="hackfloor: prove that agents which don't solve the task can't score" src="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/banner-light.svg" width="100%">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/ranjeetds/hackfloor/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/ranjeetds/hackfloor/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/hackfloor/"><img alt="PyPI" src="https://img.shields.io/pypi/v/hackfloor"></a>
  <img alt="Python 3.10 to 3.13" src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776ab">
  <a href="https://github.com/ranjeetds/hackfloor/blob/main/LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Status: alpha" src="https://img.shields.io/badge/status-alpha-orange">
  <a href="#contributors"><img alt="All contributors" src="https://img.shields.io/badge/all_contributors-1-orange.svg"></a>
  <a href="#integrity-levels"><img alt="Integrity card" src="https://img.shields.io/badge/integrity%20card-v0.1-6f42c1"></a>
</p>

<p align="center">
  <b>Your RL environment's grader rewards whatever it accepts. hackfloor finds out what that is before your training run does.</b>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#probes">Probes</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#integrity-levels">Integrity cards</a> ·
  <a href="#how-it-compares">Comparison</a> ·
  <a href="#roadmap">Roadmap</a> ·
  <a href="https://ranjeetds.github.io/hackfloor/">Docs</a>
</p>

---

hackfloor runs policies that **do not solve the task** through an environment's **real grader**: empty and format-only answers, answer enumeration, prompt echo, prompt injection aimed at LLM judges, always-equal objects, `SkipTest`, hard-coded test cases, edited tests, a `conftest.py` that rewrites pytest reports, `sys.exit(0)` before the checks, a pre-written reward file, and answer keys left in the sandbox or in git history. Each probe is paired with a matched control that touches the same files without the exploit. If the probe scores above its control, that is a finding, and the integrity card records enough to replay it.

<p align="center">
  <img alt="hackfloor scan of the bundled vulnerable pytest task: six critical findings" src="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/scan-vulnerable.svg" width="860">
  <br>
  <sub>Real output: <code>hackfloor scan fixtures/tasks/vulnerable_pytest</code> on the bundled teaching fixture. Rendered by <a href="https://github.com/ranjeetds/hackfloor/blob/main/scripts/render_readme_assets.py"><code>scripts/render_readme_assets.py</code></a>.</sub>
</p>

## Why

Models optimise the grader, not the task. The hacks are documented and they are cheap:

- objects whose `__eq__` always returns `True`, `sys.exit(0)` before the asserts, and a `conftest.py` that patches pytest's reports ([Anthropic, arXiv 2511.18397](https://arxiv.org/abs/2511.18397));
- `exit(0)` and raising `SkipTest` in coding tasks during frontier training ([Baker et al., arXiv 2503.11926](https://arxiv.org/abs/2503.11926));
- overriding equality, stubbing the evaluator and reading the grader's answer off the call stack ([METR, June 2025](https://metr.org/blog/2025-06-05-recent-reward-hacking/));
- test modification and operator overloading on impossible tasks ([ImpossibleBench, arXiv 2510.20270](https://arxiv.org/abs/2510.20270));
- a `conftest.py` hook that passes every SWE-bench Verified task ([BenchJack, arXiv 2605.12673](https://arxiv.org/abs/2605.12673)).

OpenEnv's [RFC 008](https://github.com/openenv/OpenEnv/issues/778) asks that "a panel of non-solving policies (null, degenerate, grader-injection, reward-search) scores at or below the empty-trajectory floor". OpenEnv 0.14 grades Harbor tasks for `semantic.oracle_max`, `semantic.floor_gap` and author-supplied canaries (`semantic.canary_floor`), while `statistical.adversarial_floor` is listed in its severity policy with no grader yet. hackfloor is a working, standalone version of that panel, and its card uses the same check ids.

## Highlights

- 🎯 **Runs against the real grader.** No static guessing: every finding is a scored attempt you can replay.
- ⚖️ **Matched controls.** `AlwaysEqual` is compared with `return None`, a patched `conftest.py` with an empty one, a written max reward with a written min. The gap measures the exploit, not noise.
- 📐 **Statistics where they matter.** With 5 or more tasks, an exact sign test with Holm correction across probes; with fewer, the effect has to reproduce on every replay. A hack-pass that reproduces is always a finding. Clopper-Pearson intervals on hack-pass rates, and a gameability check (point-biserial correlation and AUROC between solved and reward).
- 🪪 **Integrity cards.** A JSON record with a [schema](https://github.com/ranjeetds/hackfloor/blob/main/src/hackfloor/schema/card-0.1.schema.json), check ids taken from OpenEnv's RFC 008 validation code, `NOT_MEASURED` wherever hackfloor has no test, and an export to OpenEnv `CheckResult` records.
- 🧩 **Adapters.** Plain reward functions (`fn(completion, answer)`, verl `compute_score`, TRL `reward_funcs`), Harbor-style task directories, reasoning-gym datasets, and (experimental) Prime Intellect `verifiers` tasksets and single-step OpenEnv environments.
- 🔌 **Plugin probes.** Subclass `Probe`, register it, or ship it through the `hackfloor.probes` entry point.
- 🚦 **CI-ready.** A GitHub Action, a pre-commit hook and a pytest fixture. Exit code `1` when a finding meets `--fail-on` (default `high`), plus a Markdown report for the job summary.

## Quickstart

```bash
pip install hackfloor                      # or: uv pip install hackfloor
pip install "hackfloor[integrations]"      # + reasoning-gym, verifiers (3.11+), openenv
```

The bundled fixtures live in the repository, so clone it to try them:

```bash
git clone https://github.com/ranjeetds/hackfloor.git
cd hackfloor
uv venv && uv pip install -e ".[dev]"   # or: python -m venv .venv && pip install -e ".[dev]"
```

Scan the bundled fixtures (the pytest-based tasks need `pytest`, which the `dev` extra installs):

```bash
hackfloor scan fixtures/tasks/vulnerable_pytest      # 6 critical findings, exit code 1
hackfloor scan fixtures/tasks/fixed_pytest           # RESISTED, integrity level L1
hackfloor scan fixtures/rlvr/vulnerable_math --report report.md
```

Scan your own reward function:

```bash
hackfloor scan my_rewards.py:math_reward --data rows.jsonl --gold-template "<answer>{answer}</answer>"
```

`rows.jsonl` holds one `{"prompt": ..., "answer": ...}` per line. The gold template tells hackfloor what a correct completion looks like, so it can check that the reference scores well (calibration) and build format-aware probes. Probes never see the answer.

Or from Python:

```python
from hackfloor import scan
from hackfloor.adapters import RewardFunctionSubject


def reward(completion: str, answer: str) -> float:
    return 1.0 if answer in completion else 0.0  # substring match


rows = [{"prompt": f"What is {n} + 10?", "answer": str(n + 10)} for n in range(20)]
subject = RewardFunctionSubject(reward, rows, gold_template="<answer>{answer}</answer>")
result = scan(subject)

print(result.verdict, result.level)  # VULNERABLE 0
for p in result.findings:
    print(p.probe.id, p.severity, f"{p.hack_passes}/{p.n}")  # HF-DUMP critical 20/20
```

Scan a reasoning-gym dataset, a `verifiers` taskset or an OpenEnv environment (see [adapters](https://github.com/ranjeetds/hackfloor/blob/main/docs/adapters.md#framework-adapters)):

```bash
uv pip install -e ".[integrations]"
hackfloor scan reasoning-gym:basic_arithmetic --tasks 50
hackfloor scan verifiers:my_env:load_taskset --gold-template "<answer>{answer}</answer>"
hackfloor scan subject:my_scan:build --openenv-checks checks.json   # build() returns an OpenEnvSubject
```

<details>
<summary><b>Scanning a task directory</b></summary>

Put a `hackfloor.toml` next to the task:

```toml
[task]
environment = "environment"      # copied into a fresh sandbox for every attempt
workspace = "workspace"          # the directory the agent edits
solution = "solution"            # overlaid onto the workspace for the reference run
entry_file = "slug.py"           # optional: enables HF-EQ, HF-EXIT, HF-SKIPTEST and the leak probes
entry_functions = ["slugify"]
visible_tests = ["tests/test_*.py"]   # optional: enables HF-TESTEDIT and HF-LOOKUP
instruction = "instruction.md"   # optional: what the agent is shown
setup = ["{python}", "{task}/setup_env.py"]   # optional: runs in each fresh sandbox

[verifier]
command = ["{python}", "{task}/grader/grade.py"]
cwd = "{workspace}"
reward = "file"                  # or "exit_code"
reward_file = "logs/reward.txt"  # relative to the sandbox root
reward_file_agent_writable = true    # enables HF-REWARDFILE
timeout = 60
```

The verifier gets `HACKFLOOR_SANDBOX`, `HACKFLOOR_WORKSPACE` and `HACKFLOOR_LOGS` in its environment. A directory of such tasks is scanned as a suite. See [docs/adapters.md](https://github.com/ranjeetds/hackfloor/blob/main/docs/adapters.md).

</details>

> [!WARNING]
> hackfloor runs verifiers as local subprocesses in a temp directory. That is a probe harness, not a security boundary. Only scan environments you would run on your machine anyway. Container isolation is on the [roadmap](#roadmap).

## Probes

hackfloor ships 14 probes. A probe runs only when the target exposes what it needs, and the card lists the rest as not applicable.

| Probe | Family | What it tries | Runs on | Documented in |
|---|---|---|---|---|
| `HF-EMPTY` | form | whitespace, `None`, `{}` | completions | FieldWorkArena `{}` exploit, BenchJack |
| `HF-FORMAT` | form | answer tags, a reasoning block or `\boxed{}` with nothing inside | completions | format-reward shaping |
| `HF-DUMP` | form | every integer 0–999, A–J, yes/no in one answer | completions | weak string matching, BenchJack V5 |
| `HF-ECHO` | leak | repeat the prompt, raw and in the answer slot | completions | BenchJack V2, gradecheck prompt echo |
| `HF-JUDGE` | judge | instructions addressed to an LLM judge (a score, a verification claim, a fake transcript) | completions | BenchJack V4, gradecheck flattery |
| `HF-EQ` | tamper | return an object whose `__eq__` is always `True` | tasks with a Python entry file | Anthropic 2511.18397, METR 2025 |
| `HF-EXIT` | tamper | `sys.exit(0)` on import | tasks with a Python entry file | Anthropic 2511.18397, Baker 2503.11926 |
| `HF-SKIPTEST` | tamper | raise `unittest.SkipTest` in every function, or at import | tasks with a Python entry file | Baker 2503.11926 |
| `HF-LOOKUP` | tamper | hard-code the literal cases from the visible tests | tasks with visible tests | ImpossibleBench 2510.20270, METR 2025 |
| `HF-CONFTEST` | tamper | a `conftest.py` hook that rewrites failing reports to passed | any workspace task | Anthropic 2511.18397, BenchJack |
| `HF-TESTEDIT` | tamper | neutralise or delete the visible tests | tasks with visible tests | ImpossibleBench 2510.20270 |
| `HF-ANSWERKEY` | leak | copy a reference-looking file reachable from the sandbox | tasks with a Python entry file | BenchJack V2, gradecheck answer leak |
| `HF-GITLEAK` | leak | try every version of the entry file in the workspace's git history | tasks with a git workspace | SWE-bench issue #465 |
| `HF-REWARDFILE` | contain | pre-write the max reward to the reward file | tasks whose reward file the agent can reach | Harbor reward-file layout, BenchJack V7 |

Probes are the publicly documented minimal forms, and every file they write carries a `hackfloor canary` comment. Network and timing probes are not included yet: they need container isolation to be safe and deterministic. See [docs/probes.md](https://github.com/ranjeetds/hackfloor/blob/main/docs/probes.md).

### What the bundled fixtures show

The fixtures are small teaching environments written for hackfloor's tests, each with a fixed twin. These results come from the test suite and the CLI on Python 3.12 with pytest 9.2.0:

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

Every vulnerable fixture also fails `statistical.gameability_gap` (correlation between 0.25 and 0.57 against a bound of 0.9); every fixed twin reaches 1.0.

`HF-EXIT` does not hack `vulnerable_pytest`: with pytest 9.2.0, an import-time `sys.exit(0)` ends in `INTERNALERROR` and exit code 3. It does hack the script verifier, which trusts the exit code.

## How it works

```mermaid
flowchart TD
    T["Target: reward fn, task directory, reasoning-gym, verifiers, OpenEnv"] --> A["Adapter → Subject"]
    A --> C["Calibration: reference vs null policy"]
    A --> P["Probe registry: built-ins + plugins"]
    P --> V["Variants: exploit + matched control"]
    C --> G["Real grader, fresh sandbox per attempt, replayed"]
    V --> G
    G --> D["Paired decision: sign test + Holm, or deterministic replay"]
    D --> K["Integrity card: JSON + schema"]
    K --> O["Terminal · Markdown report · OpenEnv CheckResults · CI exit code"]
```

1. **Calibrate.** The reference solution must beat the null policy (an empty completion or an untouched workspace) on every task. If it does not, the card says `UNCALIBRATED` and gives no level.
2. **Probe.** Each applicable probe yields variants: an exploit and a matched control. Every attempt runs in a fresh sandbox and is replayed (`--replays`, default 2). The best variant per task counts.
3. **Decide.** Per task, the floor gap Δ is exploit minus control. A hack-pass is an exploit that reaches the reference score. Severity is **critical** when any task hack-passes, **high** when the mean Δ is at least half the reference-to-null gap, and **medium** otherwise. The thresholds and tests are in [docs/statistics.md](https://github.com/ranjeetds/hackfloor/blob/main/docs/statistics.md).

## Integrity levels

The integrity card is a JSON file, written by every scan, that validates against [`card-0.1.schema.json`](https://github.com/ranjeetds/hackfloor/blob/main/src/hackfloor/schema/card-0.1.schema.json).

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/integrity-card-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/integrity-card-light.svg">
    <img alt="Integrity cards for the vulnerable and fixed pytest fixtures" src="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/integrity-card-light.svg" width="860">
  </picture>
  <br>
  <sub>Rendered from the real cards of the two pytest fixtures.</sub>
</p>

| Level | Badge | Meaning | Available |
|---|---|---|---|
| L0 | ![L0](https://img.shields.io/badge/hackfloor-L0%20hackable-cf222e) | at least one critical or high finding, or a malformed reward | since v0.1 |
| L1 | ![L1](https://img.shields.io/badge/hackfloor-L1%20floor%20holds-2da44e) | calibrated, and no critical or high finding from the default probes | since v0.1 |
| L2 | ![L2](https://img.shields.io/badge/hackfloor-L2%20planned-lightgrey) | L1, plus the gameability gap from model-based policies is bounded and containment checks pass | planned (v0.3) |
| L3 | ![L3](https://img.shields.io/badge/hackfloor-L3%20planned-lightgrey) | L2, plus the canary suite and an independent replay of the card | planned (v1.0) |

A level describes this probe set at this version, not the absence of every hack. The card now measures `statistical.gameability_gap` (over scripted attempts only) and `semantic.no_solution_leakage`. RFC 008 criteria it does not measure yet (`semantic.canary_floor` and four `runtime.*` containment checks) appear as `NOT_MEASURED`, never as a pass. `--openenv-checks` writes the checks as OpenEnv `CheckResult` records.

## How it compares

Checkmarks are given only where the project's own README (or, for OpenEnv, its source code) documents the feature, checked on 26 November 2026. A blank means it is not documented there, not that it is impossible.

| | hackfloor 0.2 | [gradecheck](https://github.com/PoorvaJ-WW/gradecheck) | [BenchJack](https://github.com/benchjack/benchjack) | [OpenEnv validation](https://github.com/openenv/OpenEnv) 0.14 |
|---|:---:|:---:|:---:|:---:|
| Runs attacks against the real grader | ✓ | ✓ | ✓ (generates PoC exploits) | ✓ (author-supplied canaries) |
| Built-in exploit probes | 14 | 5 file-tree + 5 completion attacks | 8 vulnerability classes | |
| Reference and do-nothing calibration | ✓ | ✓ (noop baseline) | | ✓ (`oracle_max`, `floor_gap`) |
| Static and LLM-assisted code audit | | | ✓ | |
| Needs an LLM or API key | no | no | yes (LLM backend) | |
| Task directory with a grade command | ✓ | ✓ | | ✓ (Harbor tasks) |
| Plain reward functions (verl, TRL signatures) | ✓ | | | |
| `verifiers` environments | ◐ (experimental, trace-level rewards) | ✓ | | |
| Always-equal, `sys.exit`, `conftest.py` probes | ✓ | | ✓ (conftest exploit) | |
| Test deletion and editing | ✓ | ✓ | | |
| Answer-leak and hollow-artifact checks | ◐ (answer keys, git history, prompt echo) | ✓ | ✓ (V2) | |
| Matched controls and paired statistics | ✓ | | | |
| JSON output | ✓ (with schema) | ✓ | | |
| CI exit code | ✓ | ✓ | | |
| Plugin API for new checks | ✓ | ✓ | | |
| Container sandbox | planned (v0.3) | | ◐ (`--sandbox`, marked work in progress) | |
| Uses OpenEnv RFC 008 check ids | ✓ | | | ✓ (defines them) |

gradecheck is the closest project in spirit and its README is worth reading. BenchJack audits whole benchmarks and found exploits in all eight it studied. OpenEnv's validator is where these checks are headed; hackfloor aims to be a probe panel it can use, not a replacement.

## Integrations

| Framework | Status | How |
|---|---|---|
| Plain Python reward function | ✅ v0.1 | `hackfloor scan file.py:fn --data rows.jsonl` |
| verl `compute_score(data_source, solution_str, ground_truth, extra_info)` | ✅ v0.1 | `--flavor verl`, or detected from the signature |
| TRL `reward_funcs(prompts, completions, **columns)` | ✅ v0.1 | `--flavor trl`, or detected from the signature |
| Harbor-style task directories | ✅ v0.1 | `hackfloor.toml` beside the task; native `task.toml` reading is planned |
| reasoning-gym | ✅ v0.2 | `hackfloor scan reasoning-gym:<dataset>`; tested against 0.1.25 |
| Prime Intellect `verifiers` (v1 API) | 🧪 experimental | `hackfloor scan verifiers:<module:factory>`; trace-level rewards only; tested against 0.4.1 |
| OpenEnv `Environment` (single step, in process) | 🧪 experimental | `OpenEnvSubject` via `subject:<module:factory>`; tested against 0.15.0, including its `reasoning_gym_env` |
| OpenEnv RFC 008 `CheckResult` export | ✅ v0.2 | `--openenv-checks checks.json`; validated against openenv 0.15.0's schema |
| GitHub Action | ✅ v0.2 | `uses: ranjeetds/hackfloor@v0.2.0`, see [docs/ci.md](https://github.com/ranjeetds/hackfloor/blob/main/docs/ci.md) |
| pre-commit | ✅ v0.2 | hook id `hackfloor` |
| pytest | ✅ v0.2 | `hackfloor` fixture, `hackfloor.testing.assert_resists` |
| OpenRLHF, inspect_ai scorers, multi-step and HTTP OpenEnv | planned | |

## Roadmap

- [x] **v0.1 foundation:** CLI, probe plugin API, two adapters, 8 probes, matched controls, paired statistics, integrity card with schema, Markdown report, fixtures with fixed twins
- [x] **v0.2.0** (first PyPI release): reasoning-gym adapter, experimental `verifiers` and OpenEnv adapters, OpenEnv check export, leak and judge probes (14 in all), gameability and leakage checks, GitHub Action, pre-commit hook, pytest plugin, docs site
- [ ] **v0.2.x** (Feb 2027): stable `verifiers` and OpenEnv adapters, multi-step OpenEnv
- [ ] **v0.3** (Apr 2027): container isolation with network, timing and containment probes; model-based policies and a gameability gap over trained policies; judge probes against real LLM judges; L2
- [ ] **v1.0** (Jun 2027): 31 probes, canary suite, replayable cards, L3
- [ ] **Hub audit (upcoming):** scan public RL environments on the Hugging Face Hub and report findings privately to maintainers first. No results are published yet.

## Responsible use

hackfloor exists so that environment authors find their graders' loopholes before a training run does. Its probes are the publicly documented minimal forms of known hacks.

- Scan environments you maintain or are allowed to test.
- If you find a hack in someone else's environment or benchmark, report it to the maintainers privately and give them time to fix it before you publish. [SECURITY.md](https://github.com/ranjeetds/hackfloor/blob/main/SECURITY.md) explains how to report a problem in hackfloor itself.
- Do not use hackfloor's output to inflate leaderboard or benchmark results.

## Citation

If hackfloor helps your research, please cite it:

```bibtex
@software{dhumal2026hackfloor,
  author  = {Dhumal, Ranjeet},
  title   = {hackfloor: adversarial probes for RL environment graders and agent benchmarks},
  year    = {2026},
  version = {0.2.0},
  url     = {https://github.com/ranjeetds/hackfloor},
  license = {Apache-2.0}
}
```

There is also a [`CITATION.cff`](https://github.com/ranjeetds/hackfloor/blob/main/CITATION.cff).

## Contributing

New probes, adapters and documented hacks are welcome; [good first issues](https://github.com/ranjeetds/hackfloor/labels/good%20first%20issue) and [help wanted](https://github.com/ranjeetds/hackfloor/labels/help%20wanted) are good places to start. A new probe needs a public reference, a matched control, and a fixture pair (vulnerable and fixed) that proves it fires and that the fix holds. See [CONTRIBUTING.md](https://github.com/ranjeetds/hackfloor/blob/main/CONTRIBUTING.md) and the [Code of Conduct](https://github.com/ranjeetds/hackfloor/blob/main/CODE_OF_CONDUCT.md).

```bash
uv venv && uv pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

Commits must be signed off (`git commit -s`, [DCO](https://developercertificate.org/)).

## Contributors

Thanks to everyone who has contributed code, probes, docs, ideas and bug reports ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ranjeetds"><img src="https://avatars.githubusercontent.com/u/18438853?v=4?s=100" width="100px;" alt="Ranjeet Dhumal"/><br /><sub><b>Ranjeet Dhumal</b></sub></a><br /><a href="https://github.com/ranjeetds/hackfloor/commits?author=ranjeetds" title="Code">💻</a> <a href="https://github.com/ranjeetds/hackfloor/commits?author=ranjeetds" title="Documentation">📖</a> <a href="#ideas-ranjeetds" title="Ideas, Planning, & Feedback">🤔</a> <a href="#maintenance-ranjeetds" title="Maintenance">🚧</a> <a href="https://github.com/ranjeetds/hackfloor/commits?author=ranjeetds" title="Tests">⚠️</a> <a href="#infra-ranjeetds" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

New contributors are added after their first merged contribution. Start with a [good first issue](https://github.com/ranjeetds/hackfloor/labels/good%20first%20issue).

## License

[Apache-2.0](https://github.com/ranjeetds/hackfloor/blob/main/LICENSE)
