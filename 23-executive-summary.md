# Agent Harness Research Program — Executive Summary

**One page for busy stakeholders. Decisions required. Budget requested.**

**Author:** Anna Grace Bentley
**Date:** 2026-04-20
**Status:** Pre-registration complete; ready for pilot.

---

## The Problem

Agent performance on benchmarks (SWE-bench, OSWorld, τ-bench) increasingly
reflects **scaffolding quality**, not raw model capability. OSWorld reports
humans at 72% and agents at 12% on identical tasks — no plausible "model
capability" gap explains 60 percentage points. Most of that gap is harness.

**Today, agent benchmark scores are uninterpretable across labs** because
harness details are not reported. Two papers claiming `pass@1 = 45%` may have
scaffolds so different that comparison is meaningless.

## The Program

A four-experiment research program that **isolates each major harness
dimension** against a model-tier factorial, plus a meta-analysis tying them
together.

| Experiment | Harness dimension | Benchmark | Cost |
|------------|-------------------|-----------|:----:|
| 1. Verifier calibration | D4 verification | SWE-bench Verified | $53k |
| 2. Scaffolding shadow | D1 context policy | SWE-bench Verified | $54k |
| 3. Memory policy | D3 memory | SWE-bench Lite (longitudinal) | $2k |
| 4. Adaptive budget | D5 budget | BrowseComp | $29k |
| Meta-analysis | Cross-dimensional | — | <$1k |

**Total program:** ~$140k compute + ~4 months engineering.

## What's Ready (as of 2026-04-20)

All four protocols are **fully pre-registered** with frozen analysis plans.
Plus three cross-cutting contributions:

1. **Harness Card v1.0** — a reporting standard that makes benchmark scores
   comparable across labs. Reference implementation in pydantic; validator
   specification complete.
2. **12-pattern failure-mode taxonomy** with inter-rater-validated coding
   rubric — enables standardized failure diagnosis across agent papers.
3. **Monte-Carlo power analysis + end-to-end simulator** — protocol designs
   tested in simulation before committing real budget.

## Scientific Findings (Pre-Data)

Running the simulations *before* collecting real data has already caught
two concrete design issues:

- **Finding 1 — Sample size.** N=500 per cell gives only 77% power on the
  primary hypothesis. **Revised to N=750** (89% power) at ~$18k additional
  cost. A protocol that hadn't been simulated would have spent $35k to
  produce an underpowered null.
- **Finding 2 — Primary DV.** Under realistic LLM asymmetric miscalibration
  (Kadavath 2022 pattern), the planned primary DV (pass@1) is insensitive
  to calibration — calibration's benefit concentrates in Brier score.
  **Brier score elevated to primary DV**; H1' split into H1'a (Brier) +
  H1'b (pass@1). A protocol that hadn't been simulated would have reported
  an unresolvable "calibration null" result.

Both findings are *themselves* contributions — the paper's sidebar on
pre-registration methodology now has two worked examples.

## Decision Requested

**Go/no-go on a compute budget.** Budget sensitivity simulation
(`24-budget-sensitivity-simulation.py`, findings in `25-budget-sweet-spot.md`)
identifies three budget tiers:

| Budget | Scope | What you get |
|-------:|-------|--------------|
| **$900** | 1-week pilot, 50 tasks × 3 cells | Resolves H1'a/H1'b primary/exploratory decision. Fallback: workshop paper. |
| **$30k** | 3-tier verifier protocol at N=423 | All three primary hypotheses answered at 80% power. Scaffolding-shadow paper. |
| **$77k** | All 4 protocols at sweet-spot N | Full compound paper. Half the original $140k estimate. |
| $140k | All 4 protocols at N=750 | Tighter CIs; no new hypotheses answered over $77k. |

**$140k was the ceiling for tight CIs, not the floor for answering the
question.** The simulation-driven sweet spot is $30k (single-protocol) or
$77k (full-program).

If go, first preprint targeted at ~14 weeks with pilot + main data + full
analysis.

## What Happens If Null

Every experiment is pre-registered so that all outcomes are publishable:

- Scaffolding shadow confirmed across all 4 dimensions → strong primary paper.
- Scaffolding shadow only in some dimensions → "dimension-specific shadow"
  methodology paper.
- Scaffolding shadow rejected → "null of a widely-assumed hypothesis" — a
  major methodological result by itself.

There is no outcome that produces zero publishable work.

## Strategic Implication

If the shadow hypothesis is confirmed at the expected magnitude (~20-30pp
spread at Opus tier across policies), the practical conclusion is that
**harness engineering offers performance improvements comparable to a full
model-tier jump, at a fraction of the cost.**

That reframes how industry should invest in agent quality: not just better
models, but better *cockpits around the models*. The Harness Card standard
is the instrument that makes this investment trackable and comparable.

## Reference Materials

All materials in `/home/cisco/agent-harness-research/` (24 files, 6,000 lines,
6 runnable Python scripts). Quick entry points:

- `README.md` — directory front door
- `14-handoff-summary.md` — longer technical summary
- `15-paper-outline.md` — full paper outline with abstract
- `02-verifier-calibration-protocol.md` — primary experiment pre-registration

## Next Steps if Approved

1. **Week 0:** Approve budget. Announce pre-registration at OSF.
2. **Week 1:** Pilot study (50 tasks × 3 cells, $900). Measure verifier
   accuracy gap and miscalibration asymmetry. Freeze H1'a/H1'b primary
   status.
3. **Weeks 2-6:** Main data collection for Experiment 1 (verifier).
4. **Weeks 2-4:** Experiment 3 (memory) runs in parallel (cheapest).
5. **Weeks 4-9:** Experiment 2 (context) overlaps.
6. **Weeks 7-12:** Experiment 4 (budget).
7. **Week 13:** Meta-analysis.
8. **Weeks 14-17:** Paper draft + internal review.

---

*Full pre-registration materials, experimental protocols, and reference
implementations available in the working directory. Contact Anna Grace Bentley for
access.*
