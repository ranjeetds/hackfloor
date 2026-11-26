# Concepts in plain words

This page defines every term hackfloor uses, once. The [README](https://github.com/ranjeetds/hackfloor#readme)
and the other pages link here.

## The problem

A **reward function** (or **grader**) turns a model's answer into a number. Reinforcement
learning then pushes the model towards answers that get a high number. If the grader can be
fooled, the model learns to fool it instead of solving the task. This is called **reward
hacking**.

Hacks are usually cheap. A model does not need to be clever to find them, only to be
trained long enough against a grader that accepts them.

## What a scan does

```text
1. Calibrate   Run the reference solution and the null policy.
               The reference must score clearly higher than the null policy.
2. Probe       For every probe that applies, build two attempts:
               the hack, and a control that is the same but harmless.
3. Grade       Send each attempt through the real grader, in a fresh
               temporary directory, and repeat it (default: 2 replays).
4. Decide      Compare the hack with its control, task by task.
5. Report      Print a table, write the integrity card (JSON), and exit
               with code 1 if a finding is serious enough.
```

## Glossary

| Term | Meaning |
|---|---|
| **Target** | What you scan: a reward function, a task directory, a reasoning-gym dataset, a `verifiers` taskset or an OpenEnv environment. |
| **Adapter** | The small piece of code that lets hackfloor call a given kind of target. See [Adapters](adapters.md). |
| **Reference solution** | A correct answer for each task. In a reward-function scan it is built from the gold template. |
| **Gold template** | What a correct completion looks like, for example `<answer>{answer}</answer>`. Probes use it for the shape of an answer and never see the real answer. |
| **Null policy** | Does nothing: an empty completion, or an untouched workspace. It is the floor the grader should give. |
| **Calibration** | Checking that the reference beats the null policy on every task. If it does not, the scan stops with `UNCALIBRATED`, because nothing else can be trusted. |
| **Probe** | One documented, cheap hack, run against the grader. There are 14 built in. See [Probes](probes.md). |
| **Matched control** | An attempt that touches the same place as the hack without the hack. A patched `conftest.py` is compared with an empty one; an always-equal object is compared with `None`. The difference measures the hack, not the setup. |
| **Floor gap (Δ floor)** | The reward of the hack minus the reward of its control, averaged over tasks. |
| **Hack-pass** | A hack that reaches the reference score on a task. Reproducible hack-passes are always critical. |
| **Finding** | A probe the grader failed: the hack scored clearly above its control. Shown as `FAIL`. |
| **Severity** | `critical`: a hack-pass. `high`: the mean gap is at least half the distance from null to reference. `medium`: smaller, but still significant. |
| **Replay** | Running the same attempt again to check the result is stable. A result that does not repeat is `WARN`. |
| **Integrity card** | The JSON file every scan writes: the verdict, the level, each probe's numbers and the check ids. See [Integrity card](integrity-card.md). |
| **Integrity level** | L0 (a serious finding), L1 (calibrated and none found). L2 and L3 are planned. A level describes this probe set at this version only. |
| **Gameability** | How well the reward tracks "solved" over all scripted attempts, as a correlation. A grader that rewards non-solutions scores low. See [Statistics](statistics.md#gameability). |
| **RFC 008 check ids** | Names such as `semantic.floor_gap` taken from the OpenEnv validation proposal, so the card can be exported as OpenEnv `CheckResult` records. See [Background](background.md). |
| **NOT_MEASURED** | A check this version does not run. It is never reported as a pass. |

## How a finding is decided

- With **5 or more tasks**, a finding needs an exact one-sided sign test (hack beats control
  on more tasks than chance allows), corrected across probes with the Holm method, at
  significance 0.05, and a mean gap of at least 5% of the reward range.
- With **fewer than 5 tasks**, the gain must reproduce on every replay.
- A **reproducible hack-pass** is always critical, whatever the test says.

The formulas, intervals and bounds are in [Statistics](statistics.md).
