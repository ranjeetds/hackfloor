# Threat model

## What hackfloor answers

"Can a policy that does not solve the task get rewarded by this grader, using a known,
cheap hack?" Each finding is a concrete, replayable attempt.

## What it does not answer

- It does not prove a grader is unhackable. A clean scan means the shipped probes failed.
- It does not run model-based or search policies yet, so novel hacks found by optimisation
  are out of scope for now.
- It does not judge whether the task itself is well posed.

## Assumptions

- The agent can write anywhere in its workspace.
- `HF-REWARDFILE` assumes the agent can reach the reward file, as in a shared container. Set
  `reward_file_agent_writable = false` when the verifier runs in a separate container.
- The reference solution is correct. If it is not, calibration fails.

## Isolation

hackfloor runs verifiers as local subprocesses in a temporary directory, with your user's
permissions and environment. **This is not a security boundary.** Scan only
environments you trust to run on your machine, or run hackfloor in a container or VM.
Container isolation is planned for v0.3.

## Dual use

The probes are minimal forms of hacks already described in public work. See
[SECURITY.md](https://github.com/ranjeetds/hackfloor/blob/main/SECURITY.md) for how to handle hacks found in other people's environments.

## Responsible use

hackfloor exists so that environment authors find their graders' loopholes before a training
run does.

- Scan environments you maintain or are allowed to test.
- If you find a hack in someone else's environment or benchmark, report it to the maintainers
  privately and give them time to fix it before you publish.
- Do not use the output to inflate leaderboard scores.
- To report a problem in hackfloor itself, follow
  [SECURITY.md](https://github.com/ranjeetds/hackfloor/blob/main/SECURITY.md).
