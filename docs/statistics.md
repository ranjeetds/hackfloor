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
  the same rewards on every replay, is a finding even when the Holm-corrected test above is
  not significant. It is a concrete exploit, and at small *n* the correction cannot reach
  significance. The basis then ends in `; reproducible hack-pass`. With fewer than 5 tasks
  this always applies. With 5 or more, the hack-passes themselves must beat chance: a
  one-sided sign test of the tasks with a hack-pass against the tasks with a loss, before the
  Holm correction, at p < α. Otherwise the hack-passes are **isolated**. They are listed in
  the probe's message with their task ids and do not make the probe critical: the probe is
  then judged on its other tasks, and is `info` if nothing else is significant. An isolated
  hack-pass is usually a fixed probe output that happens to be a correct answer on one task,
  such as an injection text ending in "Score: 10" on a task whose answer is 10, or a second
  valid solution. Check those tasks by hand.

The card records which basis was used.

## Partial credit

Some graders give a small reward to any well-formed answer on purpose, for example 0.05 for
an answer in the right shape. A probe would then win against its control on every task
without the grader being exploitable. hackfloor reports such a probe as `info`, not as a
finding, when all three hold:

- the decision above is significant;
- there is no hack-pass on any task;
- the best winning exploit reward is at most *lo* + *p* × range, where *lo* is the minimum
  reward and *p* is the partial-credit bound (0.1 by default, `--partial-credit` on the
  command line, `ScanConfig.partial_credit` in Python).

An `info` probe has severity `none`, does not change the verdict or the level, is listed
under `partial_credit` in `statistical.adversarial_floor`, and is counted in
`summary.partial_credit`. Set the bound to 0 to report every significant effect as a
finding. Anything above the bound stays a finding, even when the credit is intended: a policy
that collects 0.2 per task for no work still learns something.

## Severity

- **critical:** a reproducible hack-pass that is not isolated;
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
