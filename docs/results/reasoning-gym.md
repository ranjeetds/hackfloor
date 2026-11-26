# Results: reasoning-gym 0.1.25

We scanned every dataset in [reasoning-gym](https://github.com/open-thought/reasoning-gym)
0.1.25, the latest release on PyPI on 26 November 2026, and TRL's `accuracy_reward`. Each
flagged result was re-graded by calling the dataset's own `score_answer` directly, without
hackfloor in between, and the grader code was read by hand.

**Everything on this page is specific to reasoning-gym 0.1.25.** The one real finding is
already fixed on reasoning-gym's `main` branch.

## Summary

| | Datasets |
|---|---:|
| Registered in reasoning-gym 0.1.25 | 106 |
| Scanned (100 tasks each, 2 replays) | 100 |
| Not scanned: no single reference answer (`boxnet`, `graph_color`, `propositional_logic`, `rubiks_cube`, `rush_hour`) | 5 |
| Not scanned: needs a configuration (`composite`) | 1 |
| `RESISTED` | 94 |
| `WEAK` (medium findings only) | 5 |
| `VULNERABLE` | 1 (`game_of_life_halting`) |

Every scanned dataset calibrated: the reference answer scored 1.0 and an empty completion
0.0 on every task. In all, 10,000 tasks were scanned.

## The finding: `game_of_life_halting`

In 0.1.25 the grader compares truth values of strings
(`reasoning_gym/algorithmic/game_of_life_halting.py`):

```python
if answer is not None and bool(answer) == bool(entry["answer"]):
    return 1.0
return 0.0
```

`bool("False")` is `True`, so any non-empty answer matches any reference. All five completion
probes that put text in the answer slot reach the full reward on 100 of 100 tasks:

| Probe | Variant | Reward | Reference | Hack-pass |
|---|---|---:|---:|---:|
| `HF-WRONG` | the opposite answer (`False` for `True`) | 1.00 | 1.00 | 100/100 |
| `HF-FORMAT` | `<answer>ANSWER</answer>` | 1.00 | 1.00 | 100/100 |
| `HF-DUMP` | the integers 0 to 999 | 1.00 | 1.00 | 100/100 |
| `HF-ECHO` | the prompt, inside the answer tags | 1.00 | 1.00 | 100/100 |
| `HF-JUDGE` | "Ignore all previous instructions..." inside the answer tags | 1.00 | 1.00 | 100/100 |

A policy trained on this dataset is paid for any answer at all, including the wrong one.

The bug was fixed upstream in
[open-thought/reasoning-gym@eb75607](https://github.com/open-thought/reasoning-gym/commit/eb75607658b0c37ee2ce58b98e62d1d147c42265)
("Fix bool conversion in game of life halting (#561)", 8 November 2026). The same scan
against that commit is `RESISTED` with no findings. As of 26 November 2026 the fix is not in a
PyPI release, so `pip install reasoning-gym` still installs the affected grader. If you train
on `game_of_life_halting`, install reasoning-gym from `main` or pin that commit.

## The other results

- **5 datasets are `WEAK`.** Their graders give graded partial credit to some
  non-solutions (from 0.2 up to 0.96 on the best task), and hackfloor reports credit above
  10% of the reward range as a medium finding. Apart from one isolated task, no probe
  reached the reference score on these datasets. Whether this credit matters depends on how
  the reward is used.
- **22 datasets have `INFO` results**, which do not change the verdict:
  - bounded partial credit of 0.05 for a well-formed answer (3 datasets);
  - graded credit for a near miss from `HF-WRONG`, for example a Sudoku grid with one wrong
    cell scoring 0.89 (15 datasets);
  - isolated hack-passes on 1 to 4 of 100 tasks (5 datasets). Each was checked by hand:
    a fixed probe output that happened to be a correct answer on that task, a second valid
    solution, or a numeric tolerance in the grader.
- `HF-WRONG` had an answer it could edit on 75 of the 100 datasets.

Per-dataset cards for all of these can be reproduced with the commands below.

## TRL `accuracy_reward`

`accuracy_reward` from [TRL](https://github.com/huggingface/trl) (the `_grade` function in
`trl/rewards/accuracy_rewards.py`, `main` at commit `678074b`, 13 November 2026; PyPI 1.19.0)
was scanned on 40 addition prompts with answers such as `$122$` and the gold template
`\boxed{{answer}}`. It resisted all six completion probes, with 0 hack-passes in 40 tasks for
each (95% upper bound 7.2% per probe and task). math-verify 0.9.0 was used.

## Method

- hackfloor 0.2.1 with its 15 probes. Completion graders take the 6 completion probes
  (`HF-EMPTY`, `HF-FORMAT`, `HF-DUMP`, `HF-ECHO`, `HF-JUDGE`, `HF-WRONG`); the other 9 need
  a task directory and were not applicable.
- The first 100 tasks of each dataset with seed 0, each attempt graded twice.
- The gold completion is `<answer>{answer}</answer>`. The answer is extracted with
  `reasoning_gym.utils.extract_answer` and passed to the dataset's `score_answer`.
- Findings are decided as described in [Statistics](../statistics.md): a sign test with
  Holm correction, a minimum gap of 5% of the reward range, partial credit of up to 10% of
  the range reported as `INFO`, and isolated hack-passes listed rather than counted as
  critical.
- Python 3.12.16 on Linux, 8 cores, 7 datasets in parallel. The 100 scans took 55 seconds.

## Reproduce

```bash
python -m venv .venv && . .venv/bin/activate
pip install "hackfloor[reasoning-gym]==0.2.1" "reasoning-gym==0.1.25"

# one dataset
hackfloor scan reasoning-gym:game_of_life_halting --tasks 100 --replays 2 --seed 0

# every dataset, one card each
python -c "from reasoning_gym.factory import DATASETS; print('\n'.join(sorted(DATASETS)))" |
  xargs -P 7 -I{} hackfloor scan reasoning-gym:{} --tasks 100 --replays 2 --seed 0 \
    --quiet --fail-on none --out cards/{}.json

# the upstream fix
pip install "reasoning-gym @ git+https://github.com/open-thought/reasoning-gym@eb75607658b0c37ee2ce58b98e62d1d147c42265"
hackfloor scan reasoning-gym:game_of_life_halting --tasks 100 --replays 2 --seed 0
```

For TRL, save the `_grade` logic as a plain `reward(completion, answer)` function and run:

```bash
pip install math-verify==0.9.0
hackfloor scan trl_accuracy.py:reward --data rows.jsonl \
  --gold-template '\boxed{{answer}}' --replays 2 --seed 0
```
