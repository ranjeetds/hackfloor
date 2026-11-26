# Security policy

## Reporting a vulnerability in hackfloor

Please do not open a public issue for a security problem in hackfloor itself (for example a
way for a scanned environment to escape the probe harness or tamper with an integrity card).

Report it privately through GitHub's
[private vulnerability reporting](https://github.com/ranjeetds/hackfloor/security/advisories/new)
for this repository. If that is not available to you, email ranjeetrdhumal@gmail.com with
"hackfloor security" in the subject.

Include the hackfloor version, the command you ran, and the smallest reproduction you can.
You should get an acknowledgement within 5 working days. We will agree on a disclosure date
with you; the default is 90 days after the report or when a fix is released, whichever is
sooner.

## Supported versions

hackfloor is pre-release. Only the latest commit on `main` receives fixes.

## Scope and limits

hackfloor 0.1 runs environment verifiers as local subprocesses in a temporary directory. That
is **not** a sandbox. A malicious environment can do anything your user account can. Scan
only environments you would run anyway, or run hackfloor inside a container or VM.

## Findings in other people's environments

hackfloor is built to find reward hacks. If you find one in an environment or benchmark you
do not maintain:

1. Report it privately to its maintainers, using their security policy if they have one.
2. Give them reasonable time to fix it (we suggest 90 days) before publishing details.
3. Do not use the hack to inflate results on a leaderboard or in a paper.

The probes in this repository are the minimal forms of hacks already described in public
work. Please do not contribute novel, weaponised exploits for specific live benchmarks; send
those to the benchmark's maintainers instead.
