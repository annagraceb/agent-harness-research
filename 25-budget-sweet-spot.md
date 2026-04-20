# Budget Sweet-Spot Finding

*Output of `24-budget-sensitivity-simulation.py`. A reframing of the program's
minimum-viable budget.*

---

## Headline

**The $140k figure was the ceiling for tight confidence intervals, not the
floor for answering the primary hypotheses.** At **~$30k** — a 4.7× reduction
— all three primary hypotheses of the verifier-calibration protocol remain
answerable at 80% power.

## Evidence

Running `24-budget-sensitivity-simulation.py` across budgets × tier-mixes
produces this table (best config per budget):

| Budget | Config | N/cell | Rollouts | H1'a | H1'b | H2 shadow | Answerable @80% |
|-------:|:-------|-------:|---------:|:----:|:----:|:---------:|:---------------:|
| $2k    | Sonnet only | 111 | 1,332 | ✓ | — | — | **H1'a** |
| $5k    | Sonnet only | 277 | 3,324 | ✓ | — | — | **H1'a** |
| $10k   | Sonnet only | 555 | 6,660 | ✓ | ✓ | — | **H1'a + H1'b(S)** |
| $15k   | Sonnet only | 833 | 9,996 | ✓ | ✓ | — | H1'a + H1'b(S) |
| **$30k** | **H+S+O** | **423** | **15,228** | ✓ | ✓(O) | ✓ | **H1'a + H1'b(O) + H2** |
| $50k   | H+S+O | 706 | 25,416 | ✓ | ✓(O) | ✓ | H1'a + H1'b(O) + H2 |
| $100k  | H+S+O | 1,412 | 50,832 | ✓ | ✓(O) | ✓ | same — tighter CIs |
| $140k  | H+S+O | 1,977 | 71,172 | ✓ | ✓(S) | ✓ | same — tighter CIs |

## The Sweet Spot

**$30k at 3-tier × N=423 per cell.** This configuration:

- Puts all three tiers (Haiku, Sonnet, Opus) in the experiment.
- Keeps N low but above the threshold for 80% power on each primary.
- Actually answers the scaffolding-shadow hypothesis (H2), which is the
  scientifically novel contribution.
- Costs ~$30k — within single-lab research budget, not "big-grant" territory.

**Budgets below $30k force a scoping decision:** drop either shadow (H2) or
multi-tier (H1'b at Opus). You get one cleaner paper, not the headline
compound result.

**Budgets above $50k improve confidence**, not hypothesis coverage. The
power on H2 rises from 80% at $30k to 91% at $100k — a real but incremental
gain.

## Implications for Program Scoping

### Revised Plan 3 (single verifier protocol)

- Budget: **$30k** (down from $53k)
- Sample: 3 tiers × 4 conditions × N=423 × 3 seeds = 15,228 rollouts
- Hypotheses answered: **all three primary** at 80% power
- Tradeoff: CIs are wider than at full N=750 (confidence intervals ~40% wider)

### Revised Full Program

For the compound 4-protocol paper:

| Protocol | Sweet-spot budget | Old budget |
|----------|:-----------------:|:----------:|
| Verifier (2) | $30k | $53k |
| Context (7) | ~$30k | $54k |
| Memory (8) | $2k | $2k |
| Budget (9) | ~$15k | $29k |
| **Total** | **~$77k** | **~$138k** |

**44% reduction on the full program** while retaining all primary-hypothesis
answerability. Applies the same sweet-spot principle (tier-full at lower N) to
all four protocols.

### What You Lose at $77k vs $140k

- CIs on individual cells are ~40% wider.
- Interaction effects have more variance — the cross-dimensional meta-analysis
  (`19-meta-analysis-protocol.md`) becomes marginally harder to disentangle.
- Robustness checks (prompt paraphrases, per-difficulty buckets) have less
  statistical room.

### What You Don't Lose

- Primary hypothesis answers (H1'a, H1'b, H2, Meta-M1, Meta-M2, Meta-M3).
- Publishable-regardless-of-outcome property.
- Harness Card + failure taxonomy + Pre-registration-pivot contributions.
- Reproducibility commitments.

## Even Cheaper Paths

| Plan | Cost | What you get |
|------|-----:|-------------|
| Pilot only | $900 | Resolve H1'a/H1'b primary decision. Workshop paper. |
| Sonnet-only calibration | $10-15k | H1'a + H1'b(sonnet). Single-tier paper. |
| **3-tier sweet spot** | **$30k** | **All 3 primary hypotheses of verifier protocol.** |
| Full reduced program | $77k | All 4 protocols with sweet-spot sizing. |
| Full expanded program | $140k | All 4 protocols at N=750; tight CIs. |

## Cost Levers Not Yet Explored

These would reduce cost further without changing the sim-estimated power too
much. Follow-up simulation would quantify each:

- **Stratified sampling** by SWE-bench difficulty: same power at 60% of N
  if variance is concentrated in one stratum.
- **Adaptive stopping**: stop a cell when its CI tightens enough; can save
  30-50% on cells that converge fast.
- **Shared base-agent rollouts**: across verifier variants, the agent
  trajectory up to termination is identical if verifier is a judge-only
  step. Re-use saves 3x on rollouts for V1/V2/V3 vs V0.
- **Open-weight models** (Qwen-3, Llama-4) via self-hosted GPU: ~1-2
  orders of magnitude cheaper per rollout, at cost of narrower
  external validity.

## Recommended Action

If funding is available: proceed with **$30k single-protocol sweet spot** for
the verifier experiment. Confirm the scaffolding-shadow signal is real before
scaling to the $77k full-program budget.

If not: the **$900 pilot** resolves the primary-vs-exploratory decision for
H1'b and produces a workshop paper as a fallback.
