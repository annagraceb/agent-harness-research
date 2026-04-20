# Statistical Analysis Plan (Frozen)

*This document is pre-registered alongside `02-verifier-calibration-protocol.md`.
It specifies every test that will appear in the confirmatory-analysis section of
the paper. All additional analyses are labeled exploratory.*

## 1. Data Structure

The unit of analysis is the **trajectory**. Each trajectory belongs to exactly
one cell `(tier, verifier)` and contributes one or more rollouts (3 seeds each).

Pre-computed fields per trajectory:
- `ground_truth_pass ∈ {0,1}`
- `verifier_pass ∈ {0,1,NA}` (NA when verifier=none)
- `turns_used ∈ ℤ`
- `cost_usd ∈ ℝ`
- `wall_seconds ∈ ℝ`
- `failure_mode_tag ∈ 12-category enum ∪ {NA}`

## 2. Primary Confirmatory Tests

### 2.1. H1 — Pairwise contrast within tier

For each tier `t ∈ {haiku, sonnet, opus}`:

- **Null:** `pass@1(weak-cal, t) ≤ pass@1(strong-uncal, t)`
- **Alternative (one-sided):** `pass@1(weak-cal, t) > pass@1(strong-uncal, t)`
- **Test:** two-proportion z-test (one-sided, α = 0.05)
- **Also reported:** bootstrap 95% CI on the difference (10,000 resamples, cluster
  by task_id to account for seed correlation within task)

**Multiple-comparisons correction:** Holm-Bonferroni across the three tier-level
tests.

**Pre-registered decision rule:** H1 is considered supported if at least two of
three tiers show the one-sided effect at corrected α = 0.05 AND the pooled effect
across tiers is positive with bootstrap CI excluding zero.

### 2.1a. H1' — Paired-strength calibration contrast (added 2026-04-20)

Motivated by toy-simulator finding in `13-eval-simulator-toy.py`: if the accuracy
gap between strong and weak verifiers is large, H1 as stated cannot test
calibration independently from strength. H1' isolates calibration.

**Revised 2026-04-20 (second pass)** after asymmetric-miscalibration sweep
(`20-asymmetric-miscalibration-sweep.py`): under realistic asymmetric
miscalibration, H1' stated on pass@1 can be insensitive to calibration.
H1' is therefore split into two sub-hypotheses:

#### H1'a — Calibration validity (Brier-based)

- **Null:** `Brier(strong-cal, t) ≥ Brier(strong-uncal, t)`.
- **Alternative (one-sided):** `Brier(strong-cal, t) < Brier(strong-uncal, t)`.
- **Test:** bootstrap CI on Brier difference; reject null if CI upper bound < 0.
- **Primary status:** confirmatory. Near-certain to be supported if calibration
  procedure is correctly implemented. Functions as a validity check.

#### H1'b — Calibration performance transfer (pass@1-based)

- **Null:** `pass@1(strong-cal, t) ≤ pass@1(strong-uncal, t)`.
- **Alternative (one-sided):** `pass@1(strong-cal, t) > pass@1(strong-uncal, t)`.
- **Test:** two-proportion z-test per tier; Holm-Bonferroni correction.
- **Primary status:** confirmatory **only if** pilot reveals asymmetry ratio
  (false_accept_incorrect / false_reject_correct) < 3x. If asymmetry ratio > 3x,
  H1'b is pre-registered as **expected null** — supporting prose in the paper
  should emphasize that calibration's benefit is in precision, not raw accept rate.
- **Decision:** frozen after pilot; pilot outcome documented in final protocol.

### 2.2. H2 — Scaffolding shadow (interaction)

Compute per-tier range across verifier conditions:

```
R(t) = max_{v ∈ {none,weakcal,struncal,strcal}} pass@1(v, t)
     − min_{v ∈ {none,weakcal,struncal,strcal}} pass@1(v, t)
```

- **Null:** `R(opus) − R(haiku) ≤ 0.03`
- **Alternative:** `R(opus) − R(haiku) > 0.03`
- **Test:** bootstrap CI on `R(opus) − R(haiku)`. Reject null if CI lower bound > 0.03.
- **Resamples:** 10,000; cluster by task_id; preserve within-tier-within-condition
  cell structure during resampling (block bootstrap).

### 2.3. H3 — Reliability-sensitivity (exploratory, per revised protocol)

Previously confirmatory; re-classified as exploratory after power analysis revealed
infeasible N requirement. **Still reported with full transparency** as:

- Partial η² for the verifier IV in:
  (a) two-way ANOVA on `pass@1` (tier × verifier)
  (b) same on `pass^3`
- Report both, plus their difference, with bootstrap CIs.
- No p-value is reported for H3 in the confirmatory section; the analysis is
  descriptive-exploratory.

## 3. Secondary Analyses (confirmatory)

### 3.1. Verifier Brier score per condition

Per variant, compute Brier score on the out-of-calibration experiment data:

```
Brier(v) = mean((verifier_confidence − ground_truth_pass)^2) over trajectories in cell
```

Report per-cell Brier with bootstrap CI. Pre-registered expectation: V1 and V3
Brier < 0.15, V2 Brier > 0.15 by ≥ 0.03 absolute.

### 3.2. Mediation: does calibration's effect flow through Brier?

Regress `ground_truth_pass` on:
- `verifier_condition` (dummy vars) — direct effect path
- `verifier_brier_per_cell` — mediator path

Bootstrap CI on indirect-effect (Baron-Kenny / Imai-Keele). This is exploratory
but pre-registered as part of §12 Expected Contributions.

### 3.3. Efficiency DV — Cost-adjusted accuracy

Compute per cell:

```
efficiency(v, t) = pass@1(v, t) / mean_cost_per_task(v, t)
```

Re-run H1, H2 analyses on `efficiency` as DV. Pre-register as additional primary
only if the accuracy-only findings would change interpretation (e.g., V3 wins on
raw accuracy but loses on efficiency due to high verifier cost).

## 4. Exploratory Analyses (clearly labeled)

- **Failure-mode distribution shift** across verifier conditions. Rate of
  `rubber_stamp_verification` should differ: V2 > V3 expected.
- **Turns-used distribution shift**: does verification drive fewer turns by
  short-circuiting dead-end trajectories?
- **Per-difficulty-bucket effects** on SWE-bench Verified tasks, if difficulty
  metadata is available.
- **Trajectory length × verifier accuracy**: does verifier accuracy degrade for
  long trajectories (context rot in the verifier itself)?
- **Seed variance**: decompose total variance into task-level, verifier-level,
  seed-level (variance components via random-effects model).

These are reported **in a separate section labeled Exploratory** with no
multiple-comparison correction, no formal hypothesis tests, and explicit CIs for
each point estimate.

## 5. Reporting

### 5.1. Headline table (Table 1 of the paper)

```
                 none    weak-cal   strong-uncal   strong-cal
haiku  pass@1    0.XX    0.XX       0.XX           0.XX
       pass^3    0.XX    0.XX       0.XX           0.XX
sonnet pass@1    0.XX    0.XX       0.XX           0.XX
       pass^3    0.XX    0.XX       0.XX           0.XX
opus   pass@1    0.XX    0.XX       0.XX           0.XX
       pass^3    0.XX    0.XX       0.XX           0.XX
```

Each cell ± 95% bootstrap CI.

### 5.2. Hypothesis tests table

| Hypothesis | Measure | Estimate | 95% CI | Supported? |
|------------|---------|---------:|:------:|:----------:|
| H1 (Sonnet) | pass@1 Δ | … | … | Y/N |
| H1 (Opus)   | pass@1 Δ | … | … | Y/N |
| H1 (Haiku)  | pass@1 Δ | … | … | Y/N |
| H2          | R_opus − R_haiku | … | … | Y/N |

### 5.3. Brier score table

Per cell Brier ± CI.

### 5.4. Harness Card

The frozen Harness Card v1.0 is printed in full in the methods section. Its
`frozen_hash()` (SHA-256 prefix of 16 hex chars) appears in the paper header and
is attached to every released trajectory.

## 6. Handling Surprises

**Pre-registered decision rules for unexpected outcomes:**

| Situation | Decision |
|-----------|----------|
| All calibrated variants fail Brier < 0.15 pre-experiment | Delay experiment; refine calibration procedure; document in public pre-registration update |
| Main experiment shows V0 (no verifier) beats all others | Report as-is; frames the null as the finding |
| Pilot reveals ceiling at Opus tier | Switch to SWE-bench Verified "hard" subset; re-run power analysis; update pre-registration |
| Mid-experiment: vendor silently updates a model | Halt; re-run completed cells with new snapshot; append as robustness check |

## 7. Software Stack (pinned)

- Python 3.12
- pandas 2.x (tabular I/O)
- scipy 1.13 (z-tests, bootstrap)
- statsmodels 0.14 (ANOVA, mediation)
- numpy 1.26
- All analyses in a single `run_analysis.py` script; commit hash reported with
  the paper.

## 8. Open Code, Open Data

All trajectories, verifier outputs, calibration weights, and analysis code are
released under Apache 2.0 at paper submission. Reviewers receive pre-release access
on request via double-blind review channel.

## 9. Pre-registration Metadata

- Pre-registered at: (to be filed on OSF upon pilot completion)
- Frozen date: <pilot completion date + 1 week>
- All amendments dated; original plan preserved in version control.
