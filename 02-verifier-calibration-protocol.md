# Pre-Registration: Verifier Calibration × Model Tier Factorial on SWE-bench Verified

*A pre-registered experimental protocol testing whether verifier calibration, not verifier strength, is the primary driver of agent-harness verification value.*

**Protocol version:** 1.0
**Date:** 2026-04-20
**Status:** Pre-registered — analysis plan frozen before data collection

---

## 1. Research Questions

**RQ1 (primary).** Does verifier calibration matter more than verifier strength for end-to-end agent task completion on SWE-bench Verified?

**RQ2.** Does the effect of verifier scaffolding interact with base-model capability tier? (Tests the "scaffolding shadow" hypothesis: stronger models surface more harness defects.)

**RQ3.** Does verifier scaffolding affect reliability (`pass^3`) more than it affects mean accuracy (`pass@1`)?

## 2. Background and Motivation

Prior work on agent verification (Reflexion, τ-bench, Anthropic's *Building Effective Agents*) has treated verifiers as monolithic "add-on" components, varying either their presence/absence or their underlying model. No published study to our knowledge has separated verifier **strength** (underlying model capability) from verifier **calibration** (accuracy of its pass/fail predictions).

The informal hypothesis in the field — "bigger verifier = better" — predicts monotone improvement with verifier strength. The calibration hypothesis predicts the opposite: an uncalibrated strong verifier can reject correct trajectories at high rates, causing regression relative to no verifier at all.

This protocol tests the two hypotheses against each other under a controlled factorial design on a benchmark (SWE-bench Verified) where:
- Task validity is high (Jimenez et al. 2023; verified subset by OpenAI 2024).
- Ground-truth tests are available (independent of verifier signal).
- Existing scaffolds (SWE-agent) provide a credible baseline harness.

## 3. Hypotheses

**H1 (calibration-dominance).** A weak-but-calibrated verifier yields higher `pass@1` than a strong-but-uncalibrated verifier on SWE-bench Verified at matched compute.

- Directional prediction: `pass@1(weak-cal) > pass@1(strong-uncal)` on ≥ 2 of 3 model tiers.

**H2 (scaffolding-shadow interaction).** The *spread* of `pass@1` across verifier conditions is larger at higher model tiers than at lower tiers.

- Directional prediction: `max(pass@1) − min(pass@1)` across conditions, measured at Opus tier > same spread at Haiku tier, by ≥ 3 absolute percentage points.

**H3 (reliability sensitivity).** Verifier condition explains more variance in `pass^3` than in `pass@1`.

- Operational test: partial η² for verifier IV in the ANOVA on `pass^3` exceeds partial η² for verifier IV in the ANOVA on `pass@1`.

**H4 (null/control).** The "no verifier" condition does not dominate all others. (If H4 fails to reject, the field's assumption that "verification helps" is already on shaky ground; this becomes an interesting null result.)

## 4. Design

**Type.** 4 × 3 full factorial, between-task, within-model-snapshot.

**IV1: Verifier condition (4 levels)**
- `none` — agent runs standard ReAct loop; no verifier step.
- `weak-calibrated` — small-model verifier (Haiku 4.5) whose pass/fail threshold has been temperature-calibrated on a held-out calibration set (see §7).
- `strong-uncalibrated` — Opus 4.7 verifier with default prompt, threshold = 0.5 on raw logit.
- `strong-calibrated` — Opus 4.7 verifier with temperature-scaled threshold from the same calibration procedure.

**IV2: Model tier (3 levels)**
- `haiku` — Claude Haiku 4.5 (base agent)
- `sonnet` — Claude Sonnet 4.6 (base agent)
- `opus` — Claude Opus 4.7 (base agent)

*(Verifier identity depends on condition; base agent controls the IV2 tier.)*

**Task universe.** SWE-bench Verified (500 tasks) augmented with 250 additional human-verified tasks from SWE-bench Full → 750 tasks total per cell. Tasks are assigned to cells independently (between-task across verifier conditions; all 750 seen by each model tier).

**Total cells.** 4 × 3 = 12 cells, 750 tasks each (revised up from 500 after power analysis; see `03-power-analysis.md`), 3 seeds per task for pass^k. Total: 27,000 rollouts.

*Note on task count:* SWE-bench Verified has 500 tasks; to reach N=750 per cell, we augment with SWE-bench Verified's extended split plus 250 additional verified tasks from SWE-bench Full that meet the same human-verification bar. Alternative: run all 500 tasks twice with different seeds per cell (N_effective = 1000 by seed-independent resampling). Pre-registered choice: augmentation path; documented in Appendix D.

## 5. Measurement Plan

**Primary DVs**
- `pass@1` — binary success, one rollout per task per cell, averaged.
- `pass^3` — binary success where all 3 seeds must pass (reliability metric from τ-bench).

**Secondary DVs**
- `actions_to_solve` — number of tool calls on successful rollouts (efficiency).
- `recovery_rate` — among rollouts with ≥1 failed test-run, fraction that eventually succeed.
- `verifier_rejection_rate` — fraction of trajectories verifier flagged as failing (for verifier conditions).
- `verifier_brier_score` — calibration metric: mean squared error between verifier confidence and ground-truth success (task-level, per condition).
- `dollars_per_solved_task` — API cost divided by successful tasks (efficiency under cost).

**Failure-mode tags.** Each failed trajectory coded into one of the 12 named failure patterns (§01 literature map, Section C) by an automated tagger (regex + LLM judge) + 10% human audit. See `11-failure-taxonomy-codebook.md` (planned T6) for the coding rubric.

## 6. Harness Specification (Harness Card v0.1)

To enable replication, the following harness metadata is frozen for the duration of the experiment:

*(Conforms to Harness Card v1.0 per `10-harness-card-template.md` and `04-harness-schema.py`.)*

```yaml
identity:
  name: vcal-swebench
  version: "1.0"
  # per-cell frozen_hash computed by harness_schema.HarnessCard.frozen_hash()
base_model:
  # filled per cell (haiku / sonnet / opus)
tools:
  - name: shell
    description: "non-interactive bash; 60s timeout"
    input_schema_hash: "sha256:..."
    timeout_seconds: 60
    max_output_tokens: 4000
  - name: edit
    description: "unified-diff apply; validated before write"
    input_schema_hash: "sha256:..."
    timeout_seconds: 10
    max_output_tokens: 500
  - name: search
    description: "ripgrep wrapper; truncates to 200 matches"
    input_schema_hash: "sha256:..."
    timeout_seconds: 15
    max_output_tokens: 8000
  - name: run_tests
    description: "pytest; returns summary + failing tracebacks"
    input_schema_hash: "sha256:..."
    timeout_seconds: 300
    max_output_tokens: 4000
context_policy:
  max_context_tokens: 160000
  trimming_strategy: fifo  # kept: system_prompt, tool_schemas, plan, last 20 obs
  summarizer_model: null
  plan_refresh_every_n_turns: 10
memory_policy:
  enabled: false  # D3 varies in 08-memory-write-policy-protocol
  write_gating: none
verifier:
  # VARIES PER CELL per IV1
  enabled: true  # except for V0
  # model / calibration / decision_threshold filled per variant
budget:
  max_turns: 50
  max_cost_usd: 5.00
  max_wall_seconds: 900
  allocation_strategy: fixed_uniform
permissions:
  read_scope: repo+tmp
  write_scope: repo
  network: package_install_only
  destructive_op_gating: none
recovery:
  on_consecutive_failures: 3
  on_failure_action: plan_refresh
```

## 7. Verifier Calibration Procedure

Calibration is the critical controlled variable. Procedure:

1. **Calibration set.** 50 held-out tasks from SWE-bench Lite (not in Verified). Run the agent (each tier) on each task with `no verifier`, produce labeled trajectories (success/fail by ground-truth tests).
2. **Train.** For each verifier (weak-cal, strong-cal), fit a temperature parameter `T` that minimizes NLL of the verifier's confidence scores against ground-truth labels on the calibration set. Standard Platt / temperature scaling (Guo et al. 2017).
3. **Threshold.** Set decision threshold at the cost-weighted optimal point on the calibration set (treating false-reject of a correct trajectory and false-accept of a broken trajectory as equally costly, so threshold = 0.5 after calibration).
4. **Freeze.** Temperature and threshold are frozen before main data collection.

**Uncalibrated verifier.** Uses the raw model output and threshold 0.5 — no temperature scaling. This is the naïve "just add a verifier" setup used in most ad-hoc research agents.

## 8. Controls and Confounders

**Pre-registered controls.**
- Same SWE-bench Verified snapshot (2024-10 release hash pinned).
- Same Docker image for task execution.
- Same model snapshot per tier (API pinned to explicit model IDs).
- Identical prompts for base agent across all conditions (verifier is a separate module, not a prompt change).
- Identical random seeds across tiers for seed-aligned comparison.

**Confounders pre-registered for measurement / robustness checks.**

| Confounder | Mitigation |
|------------|------------|
| Model drift mid-experiment | Record API response dates; re-run affected cells if vendor publishes a silent update |
| Prompt sensitivity | Run robustness check: 3 paraphrases of the verifier prompt, on 50-task subset; report agreement |
| Task-distribution imbalance | Stratify by SWE-bench Verified difficulty buckets (reported from pilot study) |
| Calibration-set leakage | Calibration set is disjoint from Verified; no overlapping repos |
| Evaluator leakage | SWE-bench ground-truth tests are independent of verifier model output |
| Budget asymmetry | Match total token budget per task across conditions; verifier consumes from the 5 USD cap |

## 9. Power Analysis

See `03-power-analysis.md` and `03-power-analysis.py` for the Monte-Carlo simulation and cell-size recommendation. Summary:

- **N = 750 tasks per cell** achieves 89% power for H1 (Sonnet tier) and 85% for H2.
- H3 is irreducibly under-powered at feasible N under current priors; re-classified as **exploratory-only** in this revision.
- At Haiku tier the absolute pairwise effect is small (~2pp); H1 is primarily reported at Sonnet and Opus.
- Estimated cost at N=750: ~$53,000 USD. Reduced fallback (N=400): ~$28,000 with reduced power.

## 10. Analysis Plan (frozen)

**Primary analysis (for H1).**
- Two-way ANOVA on `pass@1` with factors {verifier, tier} and interaction.
- Planned contrast: `weak-cal − strong-uncal` at each tier.
- Report: mean difference, bootstrap 95% CI (10,000 resamples, cluster by task), two-sided p.

**H2 analysis.**
- Compute per-tier range `R_tier = max_cell − min_cell` (over verifier conditions).
- Test: `R_opus > R_haiku + 3pp` with bootstrap CI on the difference.

**H3 analysis.**
- Compute partial η² for the verifier IV in separate ANOVAs on `pass@1` and `pass^3`.
- Report the difference with bootstrap CI.

**Exploratory (not pre-registered as confirmatory).**
- Per-failure-mode breakdown: does "rubber-stamp verification" rate differ across calibration conditions?
- Verifier Brier score as a mediator: does calibration explain `pass@1` through Brier, or directly?
- Budget-adjusted accuracy (accuracy at matched cost).

**Multiple comparisons.** Primary hypotheses are three (H1, H2, H3). Holm-Bonferroni correction applied. All exploratory analyses reported as such.

**Stopping rule.** No interim peeks; full data collection before any hypothesis test.

## 11. Reproducibility Commitments

- All trajectories (prompts, tool I/O, verifier outputs) logged and released as a dataset.
- Harness code released under Apache 2.0.
- Harness Card v1.0 (above) published alongside results.
- Pre-registration timestamp: included in release metadata.
- Expected cost: 27,000 rollouts × ~$2 average = ~$53,000. Budget fallback: N=400/cell for ~$28k with reduced H1 power.

## 12. Expected Contributions

Irrespective of outcome, this experiment produces three contributions to the field:

1. **First published separation of verifier strength from verifier calibration** — either H1 is supported (calibration dominates), challenging current practice; or H1 is rejected (strength dominates), reinforcing it but quantifying the effect.
2. **First direct test of the scaffolding shadow hypothesis** via the verifier lens. Establishes whether harness-model interaction effects are measurable at scale.
3. **First Harness Card published alongside an agent paper.** Introduces the reporting standard as a live artifact, not just a proposal.

## 13. Timeline (if funded)

| Phase | Duration |
|-------|----------|
| Pilot (50 tasks, 1 cell, verifier calibration) | 1 week |
| Main data collection (18k rollouts) | 2-3 weeks |
| Analysis + robustness checks | 2 weeks |
| Writing + internal review | 2 weeks |
| **Total** | **~8 weeks** |

## 14. Risks and Pre-mortems

**Risk: Verifier calibration is already near-optimal in strong models.**
Mitigation: Pilot study measures baseline Brier; if strong-uncalibrated is already well-calibrated, the comparison collapses and we widen the miscalibration gap by using a deliberately biased decision threshold.

**Risk: Weak verifier's accuracy gap dominates any calibration benefit.**
Discovered via `13-eval-simulator-toy.py`. When `P(correct | strong) ≫ P(correct | weak)` (e.g., 0.82 vs 0.70), calibration alone cannot rescue the weak verifier — strong-uncal beats weak-cal by ~7-8pp in simulation.
Mitigation: Pilot study measures per-variant accuracy *before* the full experiment. If the accuracy gap is > 10pp absolute, pre-register an **additional primary H1' (added 2026-04-20)**:
  - H1' (paired-strength contrast): `pass@1(strong-calibrated) > pass@1(strong-uncalibrated)` within each tier. This isolates pure calibration effect when paired on equal model strength.
H1' should be added to the confirmatory analysis in `06-statistical-analysis-plan.md` §2 as a second primary contrast. If pilot reveals accuracy gap < 5pp, H1' can be downgraded to exploratory.

**Risk: Under realistic asymmetric miscalibration, pass@1 is insensitive to calibration.**
Discovered via `20-asymmetric-miscalibration-sweep.py` (findings in `21-asymmetric-findings.md`). When LLM verifiers are systematically over-accepting incorrect trajectories more than over-rejecting correct ones (Kadavath 2022 pattern), calibration's benefit concentrates in **precision** (Brier score), not in raw accept rate. H1'-on-pass@1 can appear null even when calibration is working.
Mitigation: 
  - **Brier score is elevated to primary DV** for the calibration hypothesis.
  - H1' is split into **H1'a (Brier-based calibration validity)** and **H1'b (pass@1 performance transfer)**. See `06-statistical-analysis-plan.md` §2.1a.
  - Pilot must measure per-variant false-reject-correct and false-accept-incorrect rates. If asymmetry ratio > 3x, pre-register H1'b as "expected null; report Brier improvement as the main calibration finding."

**Risk: SWE-bench Verified has a success ceiling that dominates.**
Mitigation: Report per-difficulty-bucket results. If top-tier agents already saturate on easy tasks, statistical power for the interaction effect concentrates in medium/hard buckets.

**Risk: Calibration set too small.**
Mitigation: Pilot N=50 is thin; expand to N=150 if pilot Brier CIs are too wide.

**Risk: Reward hacking contaminates the signal.**
Mitigation: SWE-bench tests are hidden from the agent; reward hacking paths limited to "edit the tests" — caught by separate static check on diff.

---

## Appendix A. Verifier Prompt (strong-calibrated arm)

```
You are reviewing an agent's attempt to solve a software engineering task.

TASK: {task_description}
AGENT TRAJECTORY: {compressed_trajectory}
PROPOSED DIFF: {final_diff}

Answer TWO questions:
1. Does the diff correctly implement the required change? (yes/no)
2. Confidence (0.0-1.0) that this diff passes the hidden test suite.

Respond as JSON: {"correct": bool, "confidence": float, "reasoning": str}
```

## Appendix B. Failure-Mode Tagging Rubric (preview)

Each failed rollout assigned to exactly one primary failure mode from the 12-pattern taxonomy. See `11-failure-taxonomy-codebook.md` (T6) for full rubric. Inter-rater agreement target: κ > 0.7.

## Appendix C. Data Release Schema

Per rollout:
- `task_id`, `tier`, `verifier_condition`, `seed`
- `trajectory` (list of steps with prompts, tool calls, observations, timings)
- `final_diff`, `test_result` (ground truth)
- `verifier_output` (raw + calibrated confidence)
- `failure_mode_tag` (if applicable)
- `tokens_in`, `tokens_out`, `dollars`, `wall_seconds`
- `harness_card_hash` (Merkle hash of frozen harness config)
