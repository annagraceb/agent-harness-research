# Power Analysis — Verifier-Calibration × Model-Tier Factorial

## Summary

This power analysis supports the design in `02-verifier-calibration-protocol.md`.

**Key finding:** under our pre-registered priors, **N = 500 per cell is under-powered
for the primary pairwise test (77% detected vs 80% target)**. Recommended: revise to
**N = 750 tasks per cell**, giving 89% power on H1 and 85% on H2. H3 remains
under-powered at any feasible N and is flagged as secondary/exploratory.

**Revised sample size: N = 750 tasks per cell × 3 seeds × 12 cells = 27,000 rollouts.**

*(Original N=500 protocol revised based on actual simulation output — see §Results.)*

## Assumptions (pre-registered priors)

Priors are derived from public SWE-bench Verified leaderboards (snapshot 2026-01).
They are **priors for power calculation only** — they do not pre-commit analysis
to specific effect sizes; the analysis plan (§10 of the protocol) uses the
actually observed data.

### Prior pass@1 cell means (to be updated with pilot)

|             | none | weak-cal | strong-uncal | strong-cal |
|-------------|:----:|:--------:|:------------:|:----------:|
| **haiku**   | 0.10 | 0.13     | 0.11         | 0.15       |
| **sonnet**  | 0.32 | 0.37     | 0.30         | 0.40       |
| **opus**    | 0.52 | 0.57     | 0.49         | 0.60       |

### Prior pass^3 cell means

Derived as `pass@1 ** 1.4` (weak seed correlation; adjustable with pilot data).

## Methods

We use Monte-Carlo simulation over 1,000 experiment replications per cell size:

1. For each replication, sample Bernoulli outcomes per cell at prior rates.
2. For H1, run a one-sided two-proportion z-test (α = 0.05) comparing weak-cal
   and strong-uncal within the Sonnet tier (representative middle case).
3. For H2, compute the range of cell means within each tier and test whether
   `R_opus − R_haiku > 0.03`.
4. For H3, compute partial η² on each of `pass@1` and `pass^3` using a simplified
   additive-factor ANOVA; test whether `η²_cubed > η²_at_1`.

Why simulation instead of classical formulas: the classical Cohen-h power
calculation overstates power for proportions near 0.10 at Haiku tier and
understates variance for pass^3 (compound Bernoulli).

## Results

### H1: weak-cal > strong-uncal (Sonnet tier, 7-pp effect, one-sided z)

| N per cell | Detected at α=0.05 | Observed effect (mean) |
|-----------:|:-------------------|:----------------------:|
| 150        | 36%                | +0.072                 |
| 250        | 52%                | +0.070                 |
| 400        | 67%                | +0.070                 |
| 500        | **77%** (below target) | +0.071             |
| **750**    | **89%**            | +0.070                 |

→ **N = 750 required** to exceed 80% power for H1 at Sonnet tier.
At Haiku tier the absolute effect shrinks to ~2pp (0.13 vs 0.11), so even
N = 750 is likely under-powered there. Plan: report H1 primarily at Sonnet
and Opus, descriptively at Haiku.

### H2: scaffolding shadow (R_opus − R_haiku > 0.03)

| N per cell | Detected | Mean ΔR |
|-----------:|:---------|:-------:|
| 200        | 71%      | +0.059  |
| 350        | 76%      | +0.060  |
| 500        | 79% (marginal) | +0.059 |
| **750**    | **85%**  | +0.059  |

→ **N = 750 required** for H2 to clear 80%.

### H3: η²(pass^3) > η²(pass^1)

| N per cell | Detected |
|-----------:|:---------|
| 200        | 54%      |
| 500        | 58%      |

→ **H3 is irreducibly under-powered** under current priors — even N = 500
only detects the direction in ~58% of simulations. The effect size
(η² difference ≈ 0.001) is too small to detect with Bernoulli DVs at
feasible N. **H3 is re-classified from secondary-confirmatory to
exploratory-only** in the revised protocol.

## Revised Sample Size

| Hypothesis | Primary? | Required N | N chosen | Actual power |
|------------|:--------:|-----------:|---------:|:------------:|
| H1 pairwise contrast (Sonnet) | yes | 700+ | 750 | 89% |
| H2 interaction                | yes | 700+ | 750 | 85% |
| H3 reliability η²             | **exploratory only** | — | 750 | 58% |

→ **Revised final choice: N = 750 tasks per cell.**
4 × 3 = 12 cells × 750 × 3 seeds = **27,000 rollouts**.

## Pilot Plan

Before full data collection, run a **pilot of 50 tasks × 3 cells** (total 450 rollouts)
to:

1. Re-estimate the prior cell means (§ Assumptions above).
2. Re-run this script with updated priors.
3. Re-confirm N = 750 still clears targets; if pilot priors differ from ours, revise again.

Pilot budget estimate: ~$900 (at ~$2/rollout average across tiers).

## Cost Budget

At revised N = 750 (2,250 rollouts per tier per condition):

| Tier     | $/rollout (est.) | 2,250 rollouts | × 4 conditions |
|----------|-----------------:|---------------:|---------------:|
| Haiku    | $0.40            | $900           | $3,600         |
| Sonnet   | $1.50            | $3,375         | $13,500        |
| Opus     | $4.00            | $9,000         | $36,000        |
| **Total**|                  |                | **$53,100**    |

Reduced-scale fallback (N = 400 per cell, accept underpower on H1 at Haiku):
$28,320. Report as limited-power preliminary study if budget-constrained.

## Sensitivity Analyses (to run post-pilot)

- If pilot reveals `strong-cal` ≈ `strong-uncal` (no calibration effect): H1 fails
  by design; document as null result; proceed to report the Brier-score analysis
  as primary contribution instead.
- If pilot reveals ceiling effect at Opus tier (>70% pass@1): switch to
  SWE-bench Verified "hard" subset (145 tasks) to avoid saturation.
- If pilot reveals verifier compute cost >30% of total: report efficiency
  (pass@1 per $) as a primary DV in addition to raw accuracy.

## Reproducibility

Running `python 03-power-analysis.py` with numpy + scipy reproduces all numbers.
RNG seed: 20260420 (pinned).
