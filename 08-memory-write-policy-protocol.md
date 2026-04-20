# Pre-Registration: Memory Write-Policy Factorial — Testing Memory Pollution

*A longitudinal within-subjects protocol testing whether memory helps or hurts
agent performance over a sequence of tasks, and whether the write-gating policy
matters more than memory capacity.*

**Protocol version:** 1.0
**Date:** 2026-04-20
**Status:** Pre-registered — frozen before data collection

---

## 1. Motivation

Voyager (Wang et al. 2023) and Reflexion (Shinn et al. 2023) established that
memory helps in specific embodied and verification settings. Neither isolated
**write-gating policy** — the decision rule for *what* gets written to memory.
Anecdotally, many production agents find that naive "write everything salient"
policies degrade over time (memory pollution; Claude's named pattern).

The hypothesis from the brainstorm (H5 from the literature map): *memory writes
hurt performance unless gated by a downstream-utility signal.* This protocol
operationalizes that hypothesis in a controlled, longitudinal design.

## 2. Research Questions

**RQ1.** Do memory writes help or hurt downstream task performance over a
sequence of 50 tasks?

**RQ2.** Does a utility-gated write policy outperform salience-gated or
write-all policies?

**RQ3.** Is there a crossover point — a task index beyond which naive memory
begins hurting — and if so where?

## 3. Hypotheses

**H1 (memory pollution).** Under the `write-all` policy, mean `pass@1` on tasks
31-50 (later tasks) is *lower* than on tasks 1-20 (earlier tasks), for the same
model on the same task difficulty distribution.

- Operational: one-sided paired comparison between late-task and early-task
  accuracies on matched-difficulty subsets.

**H2 (utility-gated dominance).** `pass@1(utility-gated) > pass@1(salience-gated)`
across all 50 tasks.

**H3 (no-memory floor).** `pass@1(no-memory)` ≥ `pass@1(write-all)` on tasks 31-50.
(Predicts that naive memory is *worse* than no memory in the long run.)

**H4 (retrieval precision matters more than capacity).** Among memory-enabled
arms, `pass@1` is better predicted by retrieval precision (what fraction of
retrieved items are relevant to the current task) than by memory size (number of
items stored).

## 4. Design

**Type.** 4-arm longitudinal between-subjects on a task sequence.

**IV1: Memory write-policy (4 levels)**

| Level | Write rule | Retrieval rule |
|-------|------------|----------------|
| M0 `no-memory` | (no writes) | — |
| M1 `write-all` | every observation + every tool result summary | top-5 cosine match to current task description |
| M2 `salience-gated` | write if model confidence on observation > 0.7 OR observation flagged "surprising" | top-5 cosine match |
| M3 `utility-gated` | write only if a retrospective check says "would have helped a past task" | top-5 cosine match |

**Salience gate:** LLM self-judges observation importance 0-1; write if > 0.7.
Naive but represents common current practice.

**Utility gate:** After each task, the system asks: "Was memory item X useful in
this trajectory?" If yes, keep; if no, delete. Also: every 10 tasks, run a
batch retrospective on unused memories — delete ones not retrieved in any of
the past 10 tasks. This is the "retention by demonstrated utility" rule.

**IV2 (held fixed):** Model tier = Sonnet 4.6. Tier doesn't vary here; this
experiment is about memory policy, not tier interaction. Shadow interaction
deferred to follow-up.

**Task sequence:** 50 tasks sampled from SWE-bench Lite (100 candidates),
stratified by repo and difficulty so that the sequence is matched across arms.
**Identical task order** across arms — any order effect applies equally.

**Repeats:** 5 seeds per task per arm. `50 tasks × 4 arms × 5 seeds = 1,000
rollouts` total. Much smaller than verifier protocol due to longitudinal design.

**Verifier:** held fixed at V3 (strong-calibrated, from verifier protocol). Same
tool set, same budget, same recovery policy.

## 5. Memory System Specification

**Vector store:** in-memory FAISS with bge-small-en-v1.5 embeddings. Capped at
500 items; LRU eviction (salience) / LRU-of-unused (utility) / none (write-all
with no eviction).

**Write API:**
```python
def write(content: str, context: dict) -> str:  # returns memory_id
    ...
```

**Retrieve API:**
```python
def retrieve(query: str, top_k: int = 5) -> list[MemoryItem]:
    ...
```

**Prompt injection:** retrieved memories inserted into the agent prompt as:
```
## Relevant past experience

{formatted memory items}

## Current task

{task description}
```

## 6. Measurement Plan

**Primary DVs:**
- `pass@1` per task per arm (matched-order)
- `pass@1_late` (tasks 31-50) vs `pass@1_early` (tasks 1-20), per arm
- `memory_usage_rate` = fraction of successful rollouts that used at least one
  retrieved memory in their reasoning (judged by LLM tagger, audited on 10% sample)

**Secondary DVs:**
- `memory_pool_size_over_time` — how many items each arm keeps at each task index
- `retrieval_precision_at_5` — of the 5 retrieved items, what fraction were
  actually used? Judged retrospectively.
- `memory_pollution_rate` — of failed tasks, what fraction were failed partly
  because of a mis-retrieved memory that led the agent astray?

## 7. Analysis Plan

**H1 (memory pollution):** Paired z-test on `pass@1_late − pass@1_early` within
the `write-all` arm, one-sided (predicts late < early). Bootstrap CI.

**H2 (utility > salience):** Pooled two-proportion z-test on 50-task
`pass@1(utility)` vs `pass@1(salience)`. Bootstrap CI.

**H3 (no-memory floor):** `pass@1_late(no-memory)` vs `pass@1_late(write-all)`,
two-proportion test. Predicts no-memory wins.

**H4 (retrieval precision):** Regression:
```
pass@1 ~ beta_1 * retrieval_precision + beta_2 * memory_pool_size + controls
```
Test: `beta_1 > beta_2` in standardized units, with bootstrap CI on the
difference.

**Exploratory:**
- Does memory effect depend on task similarity across the 50-task sequence? Split
  sequence into "diverse" vs "repeated-domain" halves; re-run H1/H2.
- Survival analysis on individual memory items: distribution of item-lifetime
  under each policy.
- Item-level utility: per-item retrieval count; correlation with eventual eviction.

## 8. Power Analysis (summary)

With 50 × 5 = 250 observations per arm, detectable paired Δ is ~5pp at 80%
power on the within-arm late-vs-early test. Between-arm comparisons on the full
250 observations detect ~7pp at 80% power. Adequate for headline hypotheses;
may need more for H3 if absolute differences are small.

**Budget estimate:** 1,000 rollouts × $2 ≈ $2,000. Cheapest of the three
protocols.

## 9. Order Effects and Confounders

**Task order effect:** we use the same order across arms, so any order confound
is common. Cross-arm comparisons are thus valid for *differential* effects.

**Memory content leakage:** if a memory from task K contains task K+1's solution
verbatim, that's "cheating" in the real-world sense but *is* the intended
benefit of memory. Report both raw and "leakage-filtered" accuracy (where we
manually filter memories that literally contain answer-like content).

**Retrieval model drift:** embedding model is frozen.

**Reproducibility:** task sequence pinned by seed; FAISS index per arm saved
at each task-index checkpoint.

## 10. Pre-Mortem

- **If no difference between arms:** memory may not be the right lens; or Sonnet
  handles memory well enough that gating doesn't matter. Report as null.
- **If write-all *wins* on late tasks:** memory pollution hypothesis rejected.
  Report with follow-up hypothesis that retrieval ranks dominate write decisions.
- **If utility-gated doesn't beat salience-gated:** indicates the retrospective-
  utility signal is too weak or too delayed. Report with mechanism analysis.

## 11. Expected Contributions

1. **First controlled longitudinal test of memory write-policy** under matched-
   task conditions — isolates policy from capacity.
2. **Empirical validation (or rejection) of "memory pollution"** as a real
   failure mode vs. folklore.
3. **Retrieval-precision as a new DV** for memory systems, with method for
   automated measurement.

## 12. Combined with Verifier + Context Protocols

This protocol tests D3 (memory). Verifier protocol tests D4. Context-policy
protocol tests D1. Three dimensions tested; D2 (action), D5 (budget), D6
(permissions), D7 (recovery) remain for follow-on work.

Combined the three provide a *multi-dimensional scaffolding-shadow fingerprint*
that can be published as an empirical harness taxonomy paper.
