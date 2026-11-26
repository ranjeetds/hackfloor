# RLVR fixtures

Two reward functions for the same 40 arithmetic prompts. Answers are distinct two-digit
integers, wrapped as `<answer>NN</answer>`.

| Fixture | What it does | Known defects |
|---|---|---|
| `vulnerable_math` | +0.2 if answer tags are present, +0.8 if the reference answer appears anywhere in the tag content | format bonus above the floor (HF-FORMAT); substring match accepts an enumeration of every integer (HF-DUMP) |
| `fixed_math` | 1.0 only if the last `<answer>` block is exactly the reference integer | none known to hackfloor 0.1 |

These are teaching fixtures written for hackfloor's own tests. They are not taken from any
real project.
