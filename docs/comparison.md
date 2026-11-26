# How hackfloor compares

A "yes" is given only where the project's own README (or, for OpenEnv, its source code)
documents the feature, checked on 26 November 2026. A blank means it is not documented
there, not that it is impossible.

| | hackfloor 0.2 | [gradecheck](https://github.com/PoorvaJ-WW/gradecheck) | [BenchJack](https://github.com/benchjack/benchjack) | [OpenEnv validation](https://github.com/openenv/OpenEnv) 0.14 |
|---|:---:|:---:|:---:|:---:|
| Runs attacks against the real grader | yes | yes | yes (generates PoC exploits) | yes (author-supplied canaries) |
| Built-in exploit probes | 14 | 5 file-tree + 5 completion attacks | 8 vulnerability classes | |
| Reference and do-nothing calibration | yes | yes (noop baseline) | | yes (`oracle_max`, `floor_gap`) |
| Static and LLM-assisted code audit | | | yes | |
| Needs an LLM or API key | no | no | yes (LLM backend) | |
| Task directory with a grade command | yes | yes | | yes (Harbor tasks) |
| Plain reward functions (verl, TRL signatures) | yes | | | |
| `verifiers` environments | partial (experimental, trace-level rewards) | yes | | |
| Always-equal, `sys.exit`, `conftest.py` probes | yes | | yes (conftest exploit) | |
| Test deletion and editing | yes | yes | | |
| Answer-leak and hollow-artifact checks | partial (answer keys, git history, prompt echo) | yes | yes (V2) | |
| Matched controls and paired statistics | yes | | | |
| JSON output | yes (with schema) | yes | | |
| CI exit code | yes | yes | | |
| Plugin API for new checks | yes | yes | | |
| Container sandbox | planned (v0.3) | | partial (`--sandbox`, marked work in progress) | |
| Uses OpenEnv RFC 008 check ids | yes | | | yes (defines them) |

gradecheck is the closest project in spirit and its README is worth reading. BenchJack audits
whole benchmarks and catalogued 219 distinct flaws in eight classes across the 10 agent
benchmarks it studied ([arXiv 2605.12673](https://arxiv.org/abs/2605.12673)). OpenEnv's
validator is where these checks are headed; hackfloor aims to be a probe panel it can use,
not a replacement.
