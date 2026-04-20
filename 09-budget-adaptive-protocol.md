# Pre-Registration: Adaptive Budget Allocation — Testing Budget Myopia

*A pre-registered protocol testing whether phase-aware adaptive budget allocation
outperforms fixed-budget spending on long-horizon agent tasks.*

**Protocol version:** 1.0
**Date:** 2026-04-20
**Status:** Pre-registered — frozen before data collection

---

## 1. Motivation

The "budget myopia" failure pattern: agents spend their token/step budget
uniformly across task phases rather than front-loading exploration or reserving
capacity for debugging. Informal observations (METR time-horizon studies,
BrowseComp scaling curves) suggest budget-allocation strategies matter, but no
published experiment has *isolated* budget policy as an IV.

This protocol tests one specific budget-allocation strategy — **phase-aware
adaptive budgeting** — against the fixed-budget baseline.

## 2. Research Questions

**RQ1.** Does phase-aware adaptive budget allocation produce higher `pass@1`
on long-horizon tasks (BrowseComp, MLE-bench) at matched total budget?

**RQ2.** Where does adaptive budget help most — exploration phase, execution
phase, or recovery phase?

**RQ3.** Does an LLM have enough self-knowledge to *declare* its phase accurately,
or does phase detection need external signals?

## 3. Hypotheses

**H1 (adaptive budget wins).** At matched total budget `B_total`, phase-aware
adaptive allocation produces `pass@1 > pass@1(fixed)` on BrowseComp by ≥ 3pp.

**H2 (front-loading helps).** An "exploration-heavy" allocation (50% of budget
in first third of trajectory) outperforms uniform allocation on high-ambiguity
tasks.

**H3 (self-declared phase is unreliable).** Agent self-reported phase transitions
disagree with external oracle (trajectory-structure analysis) on > 30% of trajectories.

**H4 (budget-elasticity heterogeneity).** Some tasks are *budget-inelastic* —
more budget does not help because the failure mode is non-budget (e.g., tool
confusion). Identifying these tasks *before* allocation could save > 20% of
total budget without accuracy loss.

## 4. Design

**Type.** 4-arm between-task.

**Benchmarks:** BrowseComp (primary), MLE-bench (secondary; only if compute
allows).

**IV1: Budget policy (4 levels)**

| Level | Strategy | Token allocation per phase (early/mid/late) |
|-------|----------|---------------------------------------------|
| B0 `fixed-uniform` | equal spending, no adaptation | 33% / 33% / 33% |
| B1 `fixed-frontloaded` | static exploration-heavy | 50% / 30% / 20% |
| B2 `adaptive-self-declared` | agent declares phase; system follows | varies |
| B3 `adaptive-oracle-declared` | oracle (trajectory analyzer) declares phase | varies |

**B2 self-declared:** agent emits `<phase>research|plan|execute|verify|recover</phase>`
at each turn; budget controller adjusts token allowance per phase accordingly.

**B3 oracle-declared:** a separate LLM analyzer reviews the trajectory every 5
turns and declares phase. This is the upper bound on adaptive budget value —
compares against B2 to measure self-knowledge penalty.

**IV2 (held fixed):** model tier = Opus 4.7 (long-horizon tasks benefit most from
strong reasoning; choose the most-capable tier). Verifier = V3 strong-calibrated.
Same tool set. Context policy = C2 ledger (from shadow protocol).

**Total budget:** $B_{total}$ = 40,000 tokens per task, $5 hard cap. Constant
across arms.

**Sample size:** BrowseComp has ~1,200 questions. Use 600 stratified by category.
4 arms × 600 tasks × 3 seeds = 7,200 rollouts.

## 5. Phase Detection

**Oracle (B3) rule:**
- Phase = "research" if last 5 turns contain > 3 `search` tool calls AND no
  edit/execute calls.
- Phase = "plan" if last 3 turns contain a plan-refresh or explicit planning step.
- Phase = "execute" if last 5 turns contain > 1 `edit` or test-run call.
- Phase = "verify" if last 3 turns contain verifier invocation.
- Phase = "recover" if 2+ consecutive failures in last 3 turns.

**Self-declared (B2):** injected into every response via:
```
Begin your response with: <phase>X</phase> where X ∈ {research, plan, execute, verify, recover}
```

**Phase-to-budget mapping (same for B2 and B3):**
- research: 30% of remaining budget
- plan: 5%
- execute: 40%
- verify: 10%
- recover: 15%

(Budget allocation is *per remaining budget*, so the system renormalizes at each
phase transition.)

## 6. Measurement Plan

**Primary DVs:** `pass@1`, `pass^3`, `tokens_used`, `cost_usd`.

**Secondary DVs:**
- `phase_agreement` — fraction of turns where B2 self-declared matches B3 oracle.
- `budget_utilization_curve` — tokens spent vs task progress (per arm).
- `budget_elasticity` per task: `dpass / dbudget` estimated via bootstrap on
  sub-sampled trajectories with truncated budgets.

## 7. Analysis Plan

**H1:** Two-proportion z-test on `pass@1` (B2 + B3 pooled) vs B0. Bootstrap CI
on difference.

**H2:** Restrict to high-ambiguity BrowseComp subset (pre-filtered by an
independent judge for question ambiguity). Test `pass@1(B1) > pass@1(B0)` on
this subset.

**H3:** Compute agreement rate between B2 and B3 on per-turn phase label.
Null: agreement ≥ 0.70. Alternative: < 0.70.

**H4:** Estimate per-task budget elasticity on a 200-task subset by running 4
sub-budgets (20k, 30k, 40k, 50k tokens) for the B0 arm. Identify "inelastic"
tasks as those with `pass@1` slope < 0.001 per additional token. Report fraction
and characterize their failure modes.

**Exploratory:**
- Trajectory length vs budget savings in B2/B3.
- Failure-mode distribution per arm (does adaptive budget primarily reduce
  tool_thrash? recovery_blindness?).

## 8. Confounders

| Confounder | Mitigation |
|------------|------------|
| Phase-detection noise (B3 oracle is itself an LLM) | Use two independent phase detectors; report inter-detector agreement |
| B1 tuning advantage (50/30/20 chosen arbitrarily) | Pilot B1 with 3 candidate splits on 50-task subset; use best-performing |
| BrowseComp task-time drift (web index updates) | Pin wayback-machine snapshots where possible; report per-week buckets |

## 9. Pre-mortem

- **If fixed-uniform wins:** budget-myopia pattern is not a real failure mode at
  this budget scale. Retest with smaller total budgets (where elasticity is
  higher).
- **If adaptive wins only because of oracle B3:** confirms H3 — models can't
  self-declare phase. Ship better phase-detection systems.
- **If both B2 and B3 match B0:** phase-awareness doesn't help at this tier.
  Retest at lower tier where reasoning is weaker.

## 10. Expected Contributions

1. **First controlled test of adaptive budget on a long-horizon benchmark.**
2. **First measurement of LLM phase self-knowledge** on agent tasks.
3. **Budget-elasticity taxonomy** of tasks — identifies tasks where more budget
   won't help (useful for production systems).

## 11. Budget

7,200 rollouts × ~$4 (Opus + long trajectories) = ~$28,800.
Reduced: B3-only on 300 tasks for ~$4,800 as a pilot.

## 12. Relation to Other Protocols

- Verifier protocol tests D4. Context protocol tests D1. Memory protocol tests
  D3. This protocol tests **D5 (budget)**.
- Pattern across the four protocols: test one harness dimension at a time,
  holding others fixed at "best known" values. After all four protocols run,
  a *multi-dimension interaction study* is justified (varies 2-3 dimensions
  simultaneously to detect interaction effects).

## 13. Timeline

Same 8-week cadence as other protocols. If only one secondary protocol can run,
recommend running the memory protocol first (cheapest, shortest sequence) and
this protocol second.
