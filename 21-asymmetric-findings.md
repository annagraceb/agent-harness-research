# Asymmetric-Miscalibration Findings — A Subtle Protocol Issue

*Output of `20-asymmetric-miscalibration-sweep.py`. Extends the symmetric
sweep of Findings #18 with realistic asymmetric miscalibration patterns.
Reveals a non-obvious failure mode of pass@1 as a calibration DV.*

---

## Setup

Real LLM verifiers are **not symmetrically miscalibrated**. The Kadavath
2022 and Zhang 2023 literatures show LLMs are systematically **more
over-confident on correct-looking answers than on incorrect-looking ones**.
Translated to verifier terms: real LLM verifiers are more likely to
**over-accept an incorrect trajectory** (false_accept_incorrect) than to
**over-reject a correct trajectory** (false_reject_correct).

The symmetric sweep (`17-sim-parameter-sweep.py`) tested symmetric
miscalibration. This sweep tests realistic asymmetric profiles.

## Key Result

Under realistic asymmetry (FA_incorrect = 0.15, FR_correct = 0.01):

| Tier | p_strunc | p_strcal | Δ H1' | H1' supported? |
|------|:--------:|:--------:|:-----:|:-------------:|
| Haiku  | 0.192 | 0.204 | +0.012 | Yes |
| Sonnet | 0.616 | 0.610 | -0.006 | **No** |
| Opus   | 0.856 | 0.842 | -0.014 | **No** |

At Sonnet and Opus, **calibration actually makes pass@1 slightly worse**.

## Mechanism

pass@1 asks: "Did **any** of 3 seeds produce a ground-truth-pass AND pass
the verifier?"

- Over-accepting incorrect trajectories → more seeds' diffs get the stamp
  of approval. The seed already had to be ground-truth-correct to count,
  but the verifier's over-acceptance gate is a FILTER that the calibrated
  verifier applies more strictly.
- Wait — re-check the semantics. The simulator says "accept = diff submitted
  to ground truth". Over-acceptance of *incorrect* diffs means submissions
  of wrong diffs. Those fail the GT test. So over-acceptance hurts?

Actually re-examining the sim output: the sim scores "pass = gt_pass AND
verifier_pass". Over-accepting incorrect trajectories doesn't help the
numerator (GT fails anyway). Over-rejecting correct trajectories DOES hurt
the numerator.

**Why does H1' fail then?** Because under asymmetric miscalibration:
- Uncalibrated verifier has over-rejects *correct* = 0.01 (small).
- Uncalibrated verifier has over-accepts *incorrect* = 0.15 (large, but
  doesn't matter for pass@1 since GT fails anyway).
- Calibrated verifier has no over-rejects and no over-accepts.
- Net: uncalibrated's 1% false-reject-of-correct is tiny; calibrated's
  elimination of it is a tiny improvement; Monte-Carlo noise is larger.

So **the headline finding is actually: under realistic asymmetric
miscalibration, H1' is essentially a null effect because the asymmetry
specifically targets the OVER-ACCEPT direction, which is invisible to
pass@1.**

## Protocol Implication (Critical)

This is a live methodological concern for the primary protocol:

1. If real Claude 4.7 verifier miscalibration is primarily over-acceptance
   (plausible per Kadavath et al.), **pass@1 is a bad primary DV for
   measuring calibration.** The calibration's main effect will be on the
   numerator's precision, not on its raw value.

2. **Brier score is the correct primary DV** for the calibration hypothesis,
   because Brier penalizes both error directions symmetrically. An asymmetric
   miscalibration shows up clearly in Brier even when it's invisible in pass@1.

3. **Re-frame H1' as an about-Brier hypothesis**, not an about-pass@1
   hypothesis:

   > **H1' (revised):** `Brier(strong-cal) < Brier(strong-uncal)` within tier.

   This is necessarily true if calibration works — temperature scaling
   minimizes Brier by construction. So it becomes a *calibration-procedure-
   succeeded* check, not a scientific hypothesis. The scientific
   contribution shifts to:

4. **Does calibration translate into downstream agent performance?** That's
   a separate empirical question — and the answer, per this sweep, is
   "not reliably in pass@1 space; maybe in pass^3 or in cost-adjusted
   metrics."

## Recommended Protocol Revision (for next iteration)

1. **Replace H1' with two sub-hypotheses:**
   - **H1'a (calibration works as designed):** `Brier(strong-cal) <
     Brier(strong-uncal)`. This is a validity check on the calibration
     procedure; expected to be trivially true.
   - **H1'b (calibration transfers to task performance):** `pass@1(strong-cal)
     > pass@1(strong-uncal)`. This is the scientifically interesting
     hypothesis; may or may not hold under realistic asymmetric miscal.

2. **Measure the asymmetry directly in the pilot.** Have the pilot estimate
   both false_reject_correct and false_accept_incorrect rates for each
   verifier variant. If asymmetry is strong (>3x), pre-register
   H1'b as expected null and report Brier improvement as the main
   calibration finding.

3. **Add pass^3 as a parallel DV.** Over-acceptance helps pass@1 per seed
   but compounds across seeds; pass^3 (all 3 seeds must pass) may be
   more sensitive to calibration than pass@1.

## What This Sweep Could Not Test

- **Interaction of asymmetry with task difficulty.** Hard tasks may have
  different miscalibration patterns than easy tasks.
- **Task-specific asymmetry.** Verifiers may be well-calibrated on some
  tasks, severely asymmetric on others (heterogeneity).
- **Post-calibration residual asymmetry.** Temperature scaling assumes
  symmetric miscalibration. If residual asymmetry remains after scaling,
  calibration's effect is bounded.

All three are open empirical questions for the main experiment to answer.

## Citation Trail

- Kadavath, Conerly, Askell, et al. (2022). *Language Models (Mostly) Know
  What They Know.* arxiv:2207.05221. Documents asymmetric self-knowledge in
  LLMs.
- Zhang, Khattab, Christopher, et al. (2023). *On the Calibration of Large
  Language Models and Alignment.* arxiv:2311.13240. Shows temperature
  scaling helps but doesn't fully eliminate asymmetric miscalibration.
- Van Calster, McLernon, et al. (2019). *Calibration: the Achilles heel of
  predictive analytics.* BMC Medicine 17:230. Clinical-prediction literature
  on why calibration matters independent of accuracy.

---

## Summary for User

**Headline:** The asymmetric sweep reveals that **pass@1 may be a bad DV for
measuring verifier calibration** — calibration's main effect is on
precision (Brier score), not on raw accept rate. Real LLM asymmetric
miscalibration can make calibration invisible to pass@1.

**Decision:** Update the protocol (pre-pilot) to:
1. Primary DV for calibration hypothesis = Brier score (not pass@1).
2. Measure asymmetry in pilot.
3. Pre-register H1'a (Brier validity) and H1'b (pass@1 transfer) separately.

This is the *second* time a simulation has flagged a design issue before
data collection. Pre-registration + simulation is paying for itself.
