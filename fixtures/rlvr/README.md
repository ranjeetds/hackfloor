# RLVR fixtures

`*_math`: two reward functions for the same 40 arithmetic prompts. Answers are distinct
two-digit integers, wrapped as `<answer>NN</answer>`.

`*_halting`: two reward functions for the same 40 True/False prompts, wrapped as
`<answer>True</answer>`.

| Fixture | What it does | Known defects |
|---|---|---|
| `vulnerable_math` | +0.2 if answer tags are present, +0.8 if the reference answer appears anywhere in the tag content | format bonus above the floor (HF-FORMAT); substring match accepts an enumeration of every integer (HF-DUMP) |
| `fixed_math` | 1.0 only if the last `<answer>` block is exactly the reference integer | none known to hackfloor 0.1 |
| `vulnerable_halting` | 1.0 if `bool(answer)` matches `bool(reference)` | any non-empty answer passes, including the wrong one (HF-WRONG) |
| `fixed_halting` | 1.0 only if the last `<answer>` block equals the reference, ignoring case | none known to hackfloor 0.2.1 |

These are teaching fixtures written for hackfloor's own tests. They are not taken from any
real project.
