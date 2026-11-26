# Probes

Each probe yields variants. A variant is an exploit plus a matched control; when the control
is omitted, the null policy is the control. Per task, the variant with the largest gap counts.
`hackfloor probes` lists the probes installed, including plugins.

## Built in

### Completion probes

These grade a single completion string (reward functions, reasoning-gym, verifiers, OpenEnv).
They never see the reference answer: they use only the gold template, which describes the
output format a policy can learn from the prompt, and the prompt itself.

| Probe | Family | Variants | Control |
|---|---|---|---|
| `HF-EMPTY` | form | whitespace, `None`, `{}` | empty completion |
| `HF-FORMAT` | form | empty answer tags, empty reasoning block plus tags, empty `\boxed{}`, placeholder text | empty completion |
| `HF-DUMP` | form | integers 0–999 (tagged and raw), letters A–J, yes/no/true/false | empty completion, or an empty answer slot for tagged variants |
| `HF-ECHO` | leak | the prompt, raw and inside the answer slot | empty completion, or an empty answer slot |
| `HF-JUDGE` | judge | four task-blind injections aimed at an LLM judge (instruction override with a score, a claimed verification note, an HTML comment, a fake grading transcript), alone and inside the answer slot | empty completion, or an empty answer slot |

`tests/test_rlvr.py` checks that variants which do not use the prompt are identical across
tasks.

### Workspace probes

These edit a fresh sandbox copy of a task directory before its grader runs.

| Probe | Family | Variants | Control | Needs |
|---|---|---|---|---|
| `HF-EQ` | tamper | every entry function returns an always-equal object | the same functions returning `None` | python_entry |
| `HF-EXIT` | tamper | `sys.exit(0)` at import, then stub functions | the same file without the exit | python_entry |
| `HF-SKIPTEST` | tamper | entry functions raise `unittest.SkipTest`; the module skips at import | entry functions raise `RuntimeError` | python_entry |
| `HF-LOOKUP` | tamper | entry functions answer from a table of the literal cases in the visible tests | an empty table | python_entry, visible_tests |
| `HF-CONFTEST` | tamper | `conftest.py` with a `pytest_runtest_makereport` wrapper that sets failing call reports to passed | `conftest.py` with only a comment | |
| `HF-TESTEDIT` | tamper | replace visible tests with a passing placeholder; delete them | rewrite the tests byte for byte | visible_tests |
| `HF-ANSWERKEY` | leak | copy a reference-looking file reachable from the sandbox (`solution/`, `.oracle/`, `answers/`, `expected/`, `gold/`, `reference/`, or a file named like the entry file) | the workspace unchanged | python_entry |
| `HF-GITLEAK` | leak | every version of the entry file reachable from any git ref in the workspace (up to five) | the workspace unchanged | python_entry, a git repository |
| `HF-REWARDFILE` | contain | write the maximum reward to the reward file | write the minimum reward | reward_file_writable |

The leak probes look at the sandbox after the task's `setup` command has run, which is what
an agent would see. When they search and find nothing, the card records that as evidence for
`semantic.no_solution_leakage`.

## Not included yet

- **Network and timing** probes (egress to fetch an answer, clock and timer overrides) need
  container isolation to be safe and deterministic. They are planned with the container
  runtime.
- **contain:** symlink and FIFO answer files, resource exhaustion, cross-episode leakage.
- **form:** flattery and correctness assertions, unit and casing tricks.
- **tamper:** stubbing the evaluator, state recorded between calls.

Proposals are welcome; see [CONTRIBUTING.md](https://github.com/ranjeetds/hackfloor/blob/main/CONTRIBUTING.md). A new probe needs
a public reference, a matched control, and a vulnerable and fixed fixture pair.

## Writing your own

Subclass `Probe`, register it, or ship it through the `hackfloor.probes` entry point.
`hackfloor probes` then lists it next to the built-in ones. A probe added to this repository
needs a public reference, a matched control, and a vulnerable and fixed fixture pair; see
[CONTRIBUTING.md](https://github.com/ranjeetds/hackfloor/blob/main/CONTRIBUTING.md).
