# Task fixtures

Four small agent tasks. The agent must implement `slugify(text)` in `slug.py`. Each
vulnerable verifier has a fixed twin.

| Fixture | Verifier | Defects |
|---|---|---|
| `vulnerable_pytest` | runs the agent-visible tests with pytest; writes `1.0` to the reward file on success | tests and `conftest.py` are agent-controlled; plain `==`; a pre-written reward file is never cleared |
| `fixed_pytest` | copies only `slug.py` next to hidden tests; `--noconftest`; type-aware asserts; requires every expected test to pass in the JUnit report; always rewrites the reward file | none known to hackfloor 0.1 |
| `vulnerable_script` | imports the solution, asserts with `==`, trusts the exit code | `sys.exit(0)` and always-equal objects pass |
| `fixed_script` | runs the checks in a child process; type-aware; requires a sentinel line printed after the last check | none known to hackfloor 0.1 |

These are teaching fixtures written for hackfloor's own tests, not taken from any real
project.
