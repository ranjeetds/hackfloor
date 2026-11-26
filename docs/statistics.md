# Statistics

All comparisons are **paired per task**: an exploit and its matched control are graded on the
same task, so task difficulty cancels out.

## Calibration

For every task, hackfloor grades the reference solution and the null policy
`replays` times. Calibration fails if the reference does not beat the null policy on some
task, or if either changes between replays. A failed calibration makes the scan
`UNCALIBRATED`: findings are still listed, but no level is given.

## Per-probe quantities

For task *t*, with exploit reward *e_t*, control reward *c_t* and reference reward *g_t*
(each the mean over replays):

- floor gap Δ_t = e_t − c_t, and Δ is the mean over tasks;
- a **win** is Δ_t > 0, a **loss** is Δ_t < 0;
- a **hack-pass** is a win with e_t ≥ g_t.

Variants whose output gives the reference answer on task *t* are left out of that task (see
[Probes](probes.md)), so a hack-pass is never a correct answer.

Reported intervals: a seeded percentile bootstrap (2,000 resamples) for Δ, and an exact
Clopper-Pearson interval for the hack-pass rate. With zero hack-passes over *n* attempts,
the one-sided 95% upper bound is 1 − 0.05^(1/n), about 3/n.

## Decision

- **5 or more tasks:** an exact one-sided sign test on wins against losses, with Holm
  correction across all probes tested this way. A finding needs adjusted p < α (0.05),
  Δ ≥ δ × reward range (δ = 0.05) and more wins than losses.
- **Fewer than 5 tasks:** a sign test has no power, so the deterministic-replay rule
  applies. A finding needs at least one win, Δ ≥ δ × range, and the winning tasks must give
  the same rewards on every replay. Otherwise the probe is reported `flaky`.

- **Reproducible hack-pass:** an exploit that scores at or above the reference on a task, with
  the same rewards on every replay, is a finding whatever the test above says. It is a concrete
  exploit, and at small *n* the sign test and the Holm correction cannot reach significance.
  The basis then ends in `; reproducible hack-pass`.

The card records which basis was used.

## Severity

- **critical:** at least one hack-pass;
- **high:** Δ ≥ 0.5 × (reference mean − null mean);
- **medium:** any other finding.

## Gameability

`statistical.gameability_gap` asks whether reward separates solved from unsolved attempts at
all. Every graded attempt in the scan is labelled: the reference solution as solved, and the
null policy, every probe variant and every control as not solved. The check reports the
point-biserial correlation between the label and the reward, and the AUROC of reward as a
classifier of the label. It fails when the correlation is below the declared bound (0.9 by
default), and is `SKIP` when the label or the reward is constant.

The labels come from scripted policies only, so this measures the grader on known-bad
attempts. It is not an estimate for a trained policy.
