# Pre-Registration: Cross-Dimensional Meta-Analysis — The Scaffolding Shadow Fingerprint

*The missing glue between the four single-dimension protocols. Specifies how to
combine data post-hoc to produce a single, publishable "scaffolding shadow
fingerprint" and to test whether the shadow is a general property of agent
harnesses or a dimension-specific phenomenon.*

**Protocol version:** 1.0
**Date:** 2026-04-20
**Status:** Pre-registered — frozen before data collection across ALL four
upstream protocols

---

## 1. Why a Meta-Analysis

Each of the four single-dimension protocols (`02`, `07`, `08`, `09`) tests the
scaffolding-shadow hypothesis through one harness dimension in isolation. A
positive result in any one protocol is suggestive but not general — it could
indicate that dimension has a shadow, not that scaffolding shadow is a general
property.

The meta-analysis asks the stronger question:

> **Does harness-induced performance loss grow with model capability
> *consistently* across independent harness dimensions?**

A single clean positive answer is publishable. A clean null answer (some
dimensions show shadow, others don't) is equally publishable — it tells the
field that shadow is dimension-specific and we need to hunt for the mechanism.

## 2. Upstream Data Requirements

Meta-analysis requires the four protocols' outputs to share:

1. **Harness Card v1.0** conformance for every cell (already enforced).
2. **Per-cell rollouts tagged with** `(tier, dimension_level, seed, task_id)`.
3. **Common DVs:** `pass@1`, `pass^3`, `cost_usd`, `failure_mode_tag`.
4. **Matched tier IDs:** Haiku 4.5 / Sonnet 4.6 / Opus 4.7 held constant across
   protocols. (Enforced by upstream protocol specs.)

Data format: one `trajectory.jsonl` per protocol; each line a `Trajectory`
object per `04-harness-schema.py`. Meta-analysis combines via outer join on
`(task_id, tier)`.

## 3. Primary Meta-Hypotheses

**M1 (general shadow).** The per-tier range `R(t) = max_level pass@1(level, t)
− min_level pass@1(level, t)` is positively correlated with tier capability
across all four dimensions.

- **Operationalization:** For each dimension d ∈ {D1 context, D3 memory,
  D4 verifier, D5 budget}, fit a linear regression of `R(t)` on tier-capability
  score. Test: slope > 0 in ≥ 3 of 4 dimensions with bootstrap 90% CI
  excluding zero.

**M2 (shadow magnitude invariance).** The *magnitude* of the shadow is similar
across dimensions (not one dimension dominating).

- **Operationalization:** Compute the normalized shadow magnitude per dimension:
  `ΔR_d = R_d(opus) − R_d(haiku)`. Test: coefficient of variation across
  dimensions `CV(ΔR) = std(ΔR) / mean(ΔR)` ≤ 0.5.
- **Interpretation:** `CV ≤ 0.5` indicates dimensions are comparably affected;
  `CV > 0.5` indicates one dimension dominates.

**M3 (dimensional complementarity).** Failure-mode distributions differ across
dimensions. Specifically:
- D1 context shadow primarily manifests as `context_rot` and `observation_collapse`.
- D3 memory shadow primarily manifests as `memory_pollution`.
- D4 verifier shadow primarily manifests as `rubber_stamp_verification`.
- D5 budget shadow primarily manifests as `budget_myopia` and `tool_thrash`.

- **Operationalization:** For each dimension × tier, compute the failure-mode
  distribution (from `11-failure-taxonomy-codebook.md` rubric). Test whether
  the predicted primary failure mode is the *mode* of the distribution for
  that dimension, using chi-squared goodness-of-fit against a uniform null.

## 4. Secondary Meta-Hypotheses (exploratory)

**M4.** A mixed-effects regression predicts `pass@1` from fixed effects
{tier, dimension, dimension × tier interaction} + random effect {task_id}.
Interaction term is non-zero at α = 0.05.

**M5.** The "scaffolding shadow" is larger for harness dimensions with
higher baseline failure rates. (Tests: is shadow primarily a saturation
effect, where broken scaffolds just have more room to hurt?)

**M6.** Cost-normalized scaffold returns: `ΔR_d / marginal_cost_d` is
positive for all four dimensions. (Tests: is scaffold engineering economically
worthwhile?)

## 5. The Shadow Fingerprint Figure

The headline visualization of the meta-analysis. Composed of three panels:

**Panel A — Per-dimension shadow curves.**
Four overlaid lines, one per dimension, plotting `R_d(tier)` on y-axis against
tier capability on x-axis. A positively-sloped line = shadow present. Reader
sees at a glance which dimensions show shadow.

```
  R (range of pass@1 across condition-levels within a tier)
  ^
  |           D5 budget     ___---
  |              ______---
  |         ___--     ___----  D4 verifier
  |    ____-    ___---
  |   -   ___---     _______D1 context
  |   ---          ___-
  |           ___--        D3 memory
  |       ---
  +----------------------------------->
     Haiku      Sonnet       Opus
```

**Panel B — Shadow magnitude bar chart.**
`ΔR_d = R_d(opus) − R_d(haiku)` as a bar per dimension with 95% bootstrap CI.

**Panel C — Failure-mode fingerprint heatmap.**
Rows: dimensions (D1, D3, D4, D5). Cols: 12 failure modes. Cell color: rate.
Visual signature showing each dimension "lights up" its predicted failure modes.

## 6. Statistical Details

### 6.1 Bootstrap procedure

All CIs computed via 10,000 paired-bootstrap resamples. Resampling unit:
`(task_id, seed)` pairs. This preserves task-level dependencies across
condition cells while producing independent samples for each protocol.

### 6.2 Combining across protocols

Because the four protocols use overlapping but not identical task sets
(SWE-bench Verified + 250 augmented for Protocols 1-2; SWE-bench Lite for
Protocol 3; BrowseComp for Protocol 4), inference is **dimension-within**
rather than **cross-dimension-within-task**. Meta-analytic combination uses:

- Per-dimension-per-tier point estimates of `R(t)`.
- Pooled via inverse-variance-weighted random-effects meta-regression
  (DerSimonian-Laird).
- Heterogeneity quantified via Cochran's Q and I².

### 6.3 Handling imbalanced sample sizes

- Protocol 3 (memory) has 1,000 rollouts vs. 27,000 for Protocol 1.
  Weight each dimension's contribution by `1/SE(R_d)` in the meta-regression.
- Report weighted AND unweighted meta-effects for transparency.

## 7. Pre-Registration Commitments

Before any upstream protocol collects final data, the following are frozen:

- Tier capability scale (from Anthropic model cards or equivalent proxy).
- Dimension codes (D1, D3, D4, D5 — four dimensions; D2, D6, D7 explicitly
  out of scope for this meta-analysis).
- Failure-mode taxonomy (v1.0 from `11-failure-taxonomy-codebook.md`).
- Shadow-fingerprint figure layout (above).
- Decision rules for M1 (3 of 4 slopes positive), M2 (CV ≤ 0.5), M3
  (chi-squared significant).

## 8. What the Meta-Analysis Cannot Tell You

- Whether shadow is *causal* or associational (would require active
  scaffold intervention across many models — future work).
- Whether shadow generalizes to *other model families* (OpenAI, Google,
  Meta) — pre-registered follow-up only.
- Whether shadow persists at scale (all protocols run at ≤ Opus 4.7
  capability; what happens at GPT-7 or Opus 6 is speculative).

These limitations are documented in the paper's limitations section.

## 9. Publishable Outcomes

Regardless of direction, the meta-analysis produces a publishable result:

| M1 result | M2 result | Publication angle |
|-----------|-----------|-------------------|
| Positive (3+/4 slopes positive) | CV ≤ 0.5 | "Scaffolding shadow is general." Strong paper. |
| Positive (3+/4 slopes positive) | CV > 0.5 | "Scaffolding shadow is real but dimension-dominated." Still strong. |
| 2/4 positive | — | "Scaffolding shadow is dimension-specific — which ones?" Mechanism-hunting paper. |
| ≤ 1/4 positive | — | "Scaffolding shadow hypothesis rejected at scale." Major methodological result. |

The fourth-row null is high-value — it would refute a widely-assumed but
unproven claim in the agent community.

## 10. Timeline

Meta-analysis runs **after** the four upstream protocols complete. Expected
order:

1. Protocol 1 (verifier) data + analysis: weeks 1-6.
2. Protocol 2 (context) data + analysis: weeks 4-9 (partial overlap).
3. Protocol 3 (memory) data + analysis: weeks 2-5 (cheap; runs in parallel).
4. Protocol 4 (budget) data + analysis: weeks 7-12.
5. Meta-analysis: weeks 13-14.
6. Combined paper draft: weeks 15-17.

**Critical path:** Protocol 4 (budget) is the longest. Meta-analysis is
trivially cheap compute — the cost is the upstream protocols.

## 11. Code

Reference implementation for meta-analysis: `20-meta-analysis.py` (planned).
Would take per-protocol `trajectory.jsonl` files as input and emit:
- `shadow_fingerprint.pdf` (3-panel figure).
- `meta_results.json` (all point estimates, CIs, hypothesis tests).
- `tables.tex` (publication-ready tables).

Implementation deferred to after upstream-protocol pilot data is available;
the schema is frozen here to enable pre-registration.

## 12. Integration with Harness Card Standard

Each upstream Harness Card's `evaluation.metrics_reported` field must include
`pass@1`, `pass^3`, and `failure_mode_distribution`. The meta-analysis
validator (`20-meta-analysis.py --validate`) will check this at input time
and refuse to produce the fingerprint if any upstream Harness Card is
missing required fields.

This makes the meta-analysis itself **Harness-Card-aware** — the first
concrete demonstration of how the standard enables downstream aggregation.

## 13. Authorship Contributions (draft)

- Design: shared across all four protocol teams.
- Statistical analysis: single analyst.
- Figure production: single analyst.
- Writing: all protocol teams contribute; meta-analysis lead is first author
  of the combined paper.

## 14. Open Questions

- **Alternative shadow metric.** Could use per-tier *relative* range
  `R(t) / max_cell(t)` instead of absolute. Relative is less sensitive to
  baseline differences across dimensions. Pre-registered as secondary metric.
- **Capability axis.** Tier capability can be measured by average benchmark
  score or by MMLU/AGIEval. Pre-registered: use the tier's SWE-bench Verified
  `pass@1` under `no_verifier` (from Protocol 1) as the capability proxy.
- **Multi-family extension.** The protocol is written for Claude family.
  Cross-family replication is explicitly out of scope but the design ports
  directly with new tier capability scores.

---

## Appendix A — Derivation of the Shadow-Gradient Test

We define the shadow gradient for dimension d as:

  γ_d = Cov(R_d(tier), capability(tier)) / Var(capability(tier))

where capability is measured as tier's no-verifier SWE-bench Verified pass@1.

Under the null of no shadow, γ_d = 0 in expectation.

Under the alternative (shadow present), γ_d > 0.

The M1 test is: `γ_d > 0` in at least 3 of 4 dimensions, with bootstrap
90% CIs each excluding zero.

This is equivalent to asking: "If I pick a random harness dimension, does
bad scaffolding hurt me more at stronger models?" With 4 dimensions, getting
3+ positive slopes by chance (under global null) has probability
`C(4,3) × 0.5^4 + 0.5^4 = 5/16 ≈ 0.31`. The 3-of-4 rule is thus a
moderate-strength indicator, not strong. We therefore additionally require
each positive slope's CI to exclude zero — making the false-positive rate
under null much lower (~0.05^3 ≈ 1.25e-4 if truly independent; treat as
conservative because dimensions are correlated via shared tasks).

## Appendix B — Failure-Mode Fingerprint Predictions

Pre-registered expected primary failure mode per dimension:

| Dimension | Predicted primary failure mode |
|-----------|-------------------------------|
| D1 (context) | `context_rot` or `observation_collapse` |
| D3 (memory) | `memory_pollution` |
| D4 (verifier) | `rubber_stamp_verification` |
| D5 (budget) | `budget_myopia` or `tool_thrash` |

Deviations from these predictions are interesting: either our failure
taxonomy is incomplete, or the failure modes are more entangled than we
assume. Document and investigate.
