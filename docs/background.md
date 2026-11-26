# Background

## Why graders get hacked

Models optimise the grader, not the task. The hacks are documented and they are cheap:

- objects whose `__eq__` always returns `True`, `sys.exit(0)` before the asserts, and a
  `conftest.py` that patches pytest's reports ([Anthropic, arXiv 2511.18397](https://arxiv.org/abs/2511.18397));
- `exit(0)` and raising `SkipTest` in coding tasks during frontier training ([Baker et al., arXiv 2503.11926](https://arxiv.org/abs/2503.11926));
- overriding equality, stubbing the evaluator and reading the grader's answer off the call stack ([METR, June 2025](https://metr.org/blog/2025-06-05-recent-reward-hacking/));
- test modification and operator overloading on impossible tasks ([ImpossibleBench, arXiv 2510.20270](https://arxiv.org/abs/2510.20270));
- a `conftest.py` hook that passes every SWE-bench Verified task ([BenchJack, arXiv 2605.12673](https://arxiv.org/abs/2605.12673)).

hackfloor's probes are the publicly documented minimal forms of these hacks, plus
answer enumeration, prompt echo, judge injection, and answer keys left in the sandbox or in
git history.

## OpenEnv RFC 008

OpenEnv's [RFC 008](https://github.com/openenv/OpenEnv/issues/778) asks that "a panel of
non-solving policies (null, degenerate, grader-injection, reward-search) scores at or below
the empty-trajectory floor". OpenEnv 0.14 grades Harbor tasks for `semantic.oracle_max`,
`semantic.floor_gap` and author-supplied canaries (`semantic.canary_floor`), while
`statistical.adversarial_floor` is listed in its severity policy with no grader yet.

hackfloor is a working, standalone version of that panel, and its card uses the same check
ids. See [Integrity card](integrity-card.md) and
[OpenEnv check results](adapters.md#openenv-check-results).

## Design choices

- **Runs against the real grader.** Every finding is a scored attempt you can replay.
- **Matched controls.** `AlwaysEqual` is compared with `return None`, a patched
  `conftest.py` with an empty one, a written max reward with a written min.
- **Statistics where they matter.** Exact sign test with Holm correction across probes for 5
  or more tasks; deterministic replay for fewer. Clopper-Pearson intervals on hack-pass
  rates, and a gameability check (point-biserial correlation and AUROC between solved and
  reward). See [Statistics](statistics.md).
- **Integrity cards.** A JSON record with a [schema](https://github.com/ranjeetds/hackfloor/blob/main/src/hackfloor/schema/card-0.1.schema.json),
  `NOT_MEASURED` wherever hackfloor has no test, and an export to OpenEnv `CheckResult`
  records.
- **Plugin probes.** Subclass `Probe`, register it, or ship it through the
  `hackfloor.probes` entry point.
- **CI-ready.** A GitHub Action, a pre-commit hook and a pytest fixture, with exit code `1`
  when a finding meets `--fail-on` (default `high`) and a Markdown report for the job
  summary. See [CI](ci.md).
