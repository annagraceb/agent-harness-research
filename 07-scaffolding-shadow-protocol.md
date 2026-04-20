# Pre-Registration: Context-Policy × Model-Tier Factorial — Testing the Scaffolding Shadow Hypothesis

*A pre-registered companion experiment to `02-verifier-calibration-protocol.md`.
Where the verifier protocol tests scaffolding shadow through the D4 (verification)
lens, this protocol tests it through the D1 (observation-quality) lens.*

**Protocol version:** 1.0
**Date:** 2026-04-20
**Status:** Pre-registered — frozen before data collection

---

## 1. Motivation — What This Adds

The "scaffolding shadow" hypothesis (Claude's contribution to the brainstorm):

> **Harness-induced performance losses are *larger* at higher model tiers than at
> lower ones. The stronger the underlying model, the more visible the harness bugs
> become — because the ceiling rises faster than the harness rises.**

Two consequences if true:

1. Benchmark scores cross-paper are uninterpretable: a "better" scaffold on a weak
   model may look worse than a "worse" scaffold on a strong model, because the
   scaffold-model interaction dominates.
2. Harness engineering has **increasing** returns as models improve — directly
   contrary to the folklore that stronger models "need less scaffolding."

The verifier-calibration protocol tests this through one dimension (D4). This
protocol tests through a different, independent dimension (D1) to establish that
the shadow is general, not a verifier-specific phenomenon.

## 2. Research Questions

**RQ1 (primary).** Does context-trimming policy produce a larger `pass@1` spread
at stronger models than at weaker models on SWE-bench Verified?

**RQ2.** Is the interaction effect monotone across 3 tiers? (Predicts a
strictly-increasing spread: Haiku < Sonnet < Opus.)

**RQ3.** Do specific failure modes (context rot, observation collapse) shift
monotonically with trimming policy, and does their shift interact with tier?

## 3. Hypotheses

**H1 (shadow through context policy).** The range across context policies,
`R(t) = max_c pass@1(c, t) − min_c pass@1(c, t)`, satisfies
`R(opus) − R(haiku) > 0.05`.

*(5pp threshold, chosen as a meaningful fraction of the expected Opus absolute
effect; pre-registered.)*

**H2 (monotonic shadow).** `R(haiku) < R(sonnet) < R(opus)`, with bootstrap 90%
CIs ordered accordingly.

**H3 (context-rot rate increases with context length).** Within C0 (no trimming),
per-trajectory `failure_mode_tag == context_rot` rate increases monotonically
across bins of trajectory length ∈ {<20, 20-40, >40 turns}. Tested with a
Cochran-Armitage trend test.

**H4 (semantic-trimming benefit scales with tier).** Among the trimming policies,
C3 (semantic summarization) provides the largest `pass@1` advantage over C1 (FIFO)
at Opus tier, smaller advantage at Sonnet, negligible at Haiku.

## 4. Design

**Type.** 4 × 3 full factorial, between-task, within-model-snapshot.

**IV1: Context-policy condition (4 levels)**

| Level | `trimming_strategy` value | Kept always | Behavior when limit hit |
|-------|---------------------------|-------------|-------------------------|
| C0 | `none` | everything | truncate via API limit |
| C1 | `fifo` | system prompt, tool schemas, plan, last 20 obs | keep budget under max_context_tokens |
| C2 | `ledger` | system prompt, tool schemas, plan, constraint ledger, last 10 obs | drop older observations, retain structured facts |
| C3 | `semantic` | system prompt, tool schemas, plan, summary bundle, last 5 obs | summarize older blocks into compressed recaps |

*Enum values align with `04-harness-schema.py` `ContextPolicy.trimming_strategy` and `10-harness-card-template.md` §H.4.*

Key: C0 tests "context dump" (what most naive agent harnesses do); C1 is the
current SWE-agent default; C2 tests "structured extraction"; C3 tests "lossy
compression."

**IV2: Model tier (3 levels)** — Haiku 4.5, Sonnet 4.6, Opus 4.7.

**Verifier:** held fixed at `strong-calibrated` (V3 from `05-verifier-variants.md`)
to isolate context-policy effects from verifier effects.

**Tools, budget, permissions, recovery:** held fixed per Harness Card below.

**Sample size:** 750 tasks per cell × 3 seeds = 2,250 rollouts per cell. 12 cells.
Total: 27,000 rollouts. (Matches verifier protocol; same power-analysis logic
applies because the DV structure is identical.)

**Task universe:** SWE-bench Verified + 250 augmented verified tasks (same as
verifier protocol) to reach N=750.

## 5. Harness Card (frozen)

```yaml
harness_card:
  name: "ctxshadow-swebench-v1"
  version: "1.0"
  base_loop: "react+self-verify"
  # verifier held constant at V3 strong-calibrated
  verifier:
    variant: strong-calibrated
    model: claude-opus-4-7
  tools:  # same as verifier protocol
    - shell
    - edit
    - search
    - run_tests
  context_policy:
    # VARIES PER CELL
    trimming_strategy: [none, fifo, ledger, semantic]
    max_context_tokens: 160000
    plan_refresh_every_n_turns: 10
  memory_policy: none
  budget:
    max_turns: 50
    max_cost_usd: 5.00
    max_wall_seconds: 900
  permissions:
    read: repo+tmp
    write: repo
    network: package_install_only
  recovery:
    on_consecutive_failures: 3
    action: plan_refresh
```

## 6. Measurement Plan

**Primary DVs:** `pass@1`, `pass^3`, `R(t)` (range across context policies within tier).

**Secondary DVs:**
- `trajectory_length_distribution` — do trimming policies keep trajectories short?
- `context_rot_rate` — fraction of failed trajectories tagged `context_rot`.
- `observation_collapse_rate` — fraction of failed trajectories where a critical
  observation was summarized out before use (detected by retrospective trace analysis;
  see §9).
- `tokens_per_task` — average tokens consumed by the agent loop (excluding verifier).
- `compression_fidelity` — for C2/C3 cells, fraction of ground-truth-relevant facts
  retained after trimming, judged by a held-out model on a 100-task audit subset.

## 7. Measurement Instruments — Context-Rot Detection

Context rot is the hardest failure mode to automatically detect because the agent
doesn't explicitly signal "I forgot the goal." We operationalize context rot
detection as a *retrospective* judgment on the trajectory:

**Tag rule.** A trajectory is tagged `context_rot` if ALL of:
1. Failed final test (ground truth).
2. Trajectory length > 20 turns.
3. Turn-N action is inconsistent with turn-1 goal declaration, judged by an
   independent LLM on a contrastive prompt:
   ```
   Turn-1 goal: {goal}
   Turn-N action/plan: {action}
   Are these coherent? (yes/no/partial, brief reasoning)
   ```
4. Response is "no" or "partial" AND the trajectory contains at least one
   observation in turns [N-10, N-5] that would have corrected the direction if
   the agent had attended to it.

Inter-rater agreement required > 0.70 κ on a held-out 100-task set (two
independent judges).

**Observation collapse** tag rule: A trajectory is tagged `observation_collapse`
if a critical fact was summarized/truncated before a subsequent step that needed
it, detected by:
1. Identify facts in observations that appear in the final correct diff for similar
   tasks (as reference).
2. Check whether the fact was present in verbatim form at the time the agent
   needed it, or was lost to trimming.
3. If lost and the trajectory failed, tag as observation collapse.

## 8. Predicted Results (pre-registered)

*Not a commitment; a pre-registered expectation to discipline interpretation.*

| Tier ↓ / Policy → | C0 (no-trim) | C1 (fifo) | C2 (ledger) | C3 (semantic) |
|-------------------|:------------:|:---------:|:-----------:|:-------------:|
| Haiku  | 0.09 | 0.13 | 0.13 | 0.12 |
| Sonnet | 0.25 | 0.37 | 0.39 | 0.38 |
| Opus   | 0.32 | 0.57 | 0.62 | 0.64 |

Predicted ranges: R(haiku) ≈ 0.04, R(sonnet) ≈ 0.14, R(opus) ≈ 0.32. Predicts
strong shadow: Opus is much more hurt by bad context policy than Haiku.

Predicted context_rot_rate (C0 cells): Haiku 30%, Sonnet 45%, Opus 60%. Stronger
models *use* more context, so they are more exposed to rot.

## 9. Analysis Plan (frozen)

Pointer to `06-statistical-analysis-plan.md` for shared conventions
(bootstrap CIs, Holm-Bonferroni across primary tests, block bootstrap, etc.).

Specific primary tests:

- **H1:** Bootstrap CI on `R(opus) − R(haiku)`. Reject null if CI lower bound > 0.05.
- **H2:** Pairwise ordered CIs: `R(sonnet) > R(haiku)` and `R(opus) > R(sonnet)`
  each with 90% bootstrap CI excluding zero. Both must hold.
- **H3:** Cochran-Armitage trend test on context_rot_rate across length bins
  within C0 cells only. α = 0.05 one-sided.
- **H4:** Bootstrap CI on `Δ_tier = (pass@1(C3, tier) − pass@1(C1, tier))`. Predicts
  `Δ_opus > Δ_sonnet > Δ_haiku` with 90% CIs.

**Exploratory:**
- Interaction effect in two-way ANOVA (policy × tier) on pass@1.
- Per-difficulty-bucket breakdown.
- Cost-adjusted effects.

## 10. Confounders and Robustness

| Confounder | Mitigation |
|------------|------------|
| Verifier drift between cells | Frozen V3 config (calibration T and threshold pinned) |
| Tokenizer differences across models | Report context lengths in tokens per model's own tokenizer; secondary analysis in character count |
| C3 summarizer itself injects bias | Use same summarizer model (Haiku 4.5) across all C3 cells; report summarizer ablation on 50-task subset |
| Task distribution | Stratify by SWE-bench difficulty buckets; report per-bucket |
| Model drift mid-experiment | Pin API version IDs; re-run affected cells on silent update |

## 11. Pre-mortem: What Could Invalidate the Shadow

We pre-register failure modes for the shadow hypothesis:

- **If R(haiku) ≈ R(opus):** shadow hypothesis rejected for context policy.
  Residual work: re-test via other harness dimensions (tool interface, recovery)
  before declaring shadow is a general property.
- **If R(opus) < R(haiku):** anti-shadow — stronger models are more *robust* to
  bad context. Would be a major finding; report as such.
- **If C0 dominates at all tiers:** shadow may be measurement artifact (stronger
  models benefit from more raw context, trimming always hurts). Report per-length
  bin to disambiguate.

## 12. Budget

At 27,000 rollouts × ~$2 average = ~$54,000 (comparable to verifier protocol).
**Combined cost of running verifier + shadow protocols in sequence: ~$107,000.**
Joint cost can be reduced by sharing Haiku-tier pilot data and by using shared
calibration set for V3 verifier across both experiments.

## 13. Scientific Contributions

1. **First published test of the scaffolding shadow hypothesis at scale.**
   Multi-dimension corroboration (via verifier AND context-policy lenses).
2. **First standardized context-rot detection rubric** with inter-rater
   agreement measurement.
3. **Empirical answer to "when does harness engineering matter more?"** —
   by tier and by context-length bucket.

## 14. Joint Analysis with Verifier Protocol

If both protocols run, we can pool data for a **cross-protocol shadow meta-test**:

- For each harness dimension tested (D1 context, D4 verifier), compute the per-tier
  range and the per-tier gradient `dR/d(tier)`.
- If the gradient is consistently positive across dimensions, this is strong
  evidence that scaffolding shadow is a *general* property of agent harnesses,
  not a quirk of any one dimension.

This joint analysis is pre-registered as part of the combined paper's exploratory
section.

## 15. Timeline

Same as verifier protocol: ~8 weeks end-to-end (pilot → data → analysis → write).
Can run in parallel to verifier protocol if compute budget permits (separate
SWE-bench Docker environments).
