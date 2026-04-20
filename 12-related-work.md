# Related Work

*An organized literature synthesis for the agent-harness research program. Maps
prior work onto the 7-dimension harness taxonomy and identifies precedent for
each of the four pre-registered protocols.*

---

## 1. Foundational Agent Architectures

**ReAct** (Yao, Zhao, Yu, et al. 2022, arxiv:2210.03629). The seminal
interleaved-reasoning-and-action paradigm. Establishes the tight-loop
think-act-observe pattern used as the base loop in all four of our protocols.
Does not isolate harness components — uses a fixed prompt template — but
establishes that *loop structure* matters for grounded reasoning.

**Reflexion** (Shinn, Cassano, Gopinath, et al. 2023, arxiv:2303.11366).
Introduces episodic memory and self-reflection as scaffolding components.
Shows large gains on HumanEval and AlfWorld by adding a verification+reflection
step. Relevant to D3 (memory) and D4 (verification). Does not isolate
*calibration* of the verifier — treats verification as binary "add or don't."

**Voyager** (Wang, Xie, Jiang, et al. 2023, arxiv:2305.16291). Open-ended
embodied agent with a skill library. First demonstrates that a *growing*
memory (skills) helps across long horizons in Minecraft. Relevant to D3.
Does not address memory pollution at scale — Voyager's write-gating is
heuristic and not compared to alternatives.

---

## 2. Benchmarks that Stress Harness Quality

**SWE-bench / SWE-bench Verified** (Jimenez, Yang, Wettig, et al. 2023,
arxiv:2310.06770; OpenAI's Verified subset, 2024). Real GitHub issue resolution.
Critical for our work: stresses D1 (observation — repo navigation),
D2 (action — shell/edit granularity), D4 (verification — hidden tests).
The "Verified" subset provides human-validated ground truth essential for
our calibration procedure.

**SWE-agent** (Yang, Jimenez, Wettig, et al. 2024, arxiv:2405.15793).
**The single most important precedent for the scaffolding shadow hypothesis.**
Explicitly isolates the agent-computer interface (ACI) as a variable and
shows that custom tools for search/edit/test raise pass@1 from ~4% to 12.5%.
This is a de facto scaffolding-shadow demonstration, though not framed
as such.

**τ-bench** (Yao, Shi, Shin, et al. 2024, arxiv:2406.12045). Introduces
`pass^k` as a reliability metric. Stresses D2 (action — structured APIs)
and D4 (verification — policy compliance). Our use of `pass^k` for reliability
sensitivity follows this precedent directly.

**AgentBench** (Liu, Yu, Lai, et al. 2023, arxiv:2308.03688). Eight
interactive environments. Reports that "long-term reasoning, decision-making,
and instruction-following" are recurring bottlenecks — these map directly
onto our failure patterns (context rot, plan drift, instruction bleed).
Benchmark diversity but limited harness-ablation data.

**WebArena / OSWorld** (Zhou et al. 2023; Xie et al. 2024). Realistic web
and desktop environments. OSWorld's 72% human / 12% agent gap is the
most-cited scaffolding-shadow-sized signal in the literature — almost
certainly not a "model capability" gap alone.

**BrowseComp** (OpenAI 2025). Persistent browsing tasks. Tests D5 (budget
allocation — search depth vs. breadth). Our budget-adaptive protocol's
use of BrowseComp as a benchmark follows this directly.

**MLE-bench** (OpenAI 2024). ML engineering on Kaggle tasks. Explicitly
treats resource allocation (compute, time) as a first-class evaluation axis.
Provides precedent for our adaptive-budget hypothesis.

**METR time-horizon evaluations** (METR 2024-25). Measures "50% success
time-horizon" — how long a task needs to be before agents fail with 50%
probability. Implicitly a budget-sensitivity measurement; our protocol
explicitly varies budget policy.

---

## 3. Context Management

**Lost in the Middle** (Liu, Lin, Hewitt, et al. 2023, TACL). Established
that retrieval accuracy depends on position within a long context.
Foundational for our D1 (observation quality) analysis.

**Chroma Context Rot research** (2024). Showed that longer context degrades
reasoning even when retrieval remains possible. Directly supports our
distinction between retrieval failure and reasoning failure (H1 of the
verifier protocol's earlier formulation).

**Needle-in-a-Haystack** (Kamradt 2023 and derivatives). Tests retrieval
at length but not downstream reasoning. Useful baseline; we add the
downstream-reasoning dimension.

---

## 4. Verification and Self-Criticism

**Self-Refine** (Madaan et al. 2023, arxiv:2303.17651). Introduces iterative
self-refinement. Variant of Reflexion-style verification. Does not isolate
calibration.

**Tree of Thoughts** (Yao et al. 2023, arxiv:2305.10601). Multi-branch
exploration with intermediate evaluation. Verifier-as-value-function. Uses
verification *selection*, not gating. Tangentially relevant.

**LLM Self-Knowledge** (Kadavath et al. 2022, arxiv:2207.05221). The
canonical result that LLM confidence is miscalibrated on hard tasks.
Directly motivates our protocol's calibration-first stance.

**Calibration for LLMs** (Zhang et al. 2023; Tian et al. 2023).
Temperature scaling and related methods for post-hoc calibration. We
adopt temperature scaling (Platt-style) as the pre-registered calibration
method per `02-verifier-calibration-protocol.md` §7.

---

## 5. Industry / Engineering Writing on Agent Harnesses

**Anthropic — "Building Effective Agents"** (2024). The canonical pragmatic
writeup on workflow vs. autonomous agents. Emphasizes:
- Composable simple workflows > ornate frameworks.
- Clear tool contracts.
- Bounded autonomy.

Not a research paper but an engineering synthesis. Our harness-card standard
is consistent with its "make the design explicit" thesis.

**OpenAI — Operator / GPT computer-use post-mortems** (2025). Publicly
discussed failure modes align with our 12-pattern taxonomy, especially
context rot and permission learned helplessness.

**Cognition — Devin** (2024). First highly-autonomous code agent; public
postmortems describe "wandering" behavior (our plan-execution drift pattern)
as a major failure mode.

---

## 6. Evaluation Methodology

**Model Cards** (Mitchell et al. 2019). Direct analog for our Harness Card.
We adopt the same philosophy: a lightweight, machine-readable artifact
traveling with every published result.

**Datasheets for Datasets** (Gebru et al. 2018). Earlier and broader
precedent. Informed the *required-field-set* approach in Harness Card v1.0.

**Pre-registration in ML** (Forde & Paganini 2019; Pineau et al. 2021).
Growing movement in ML to pre-register experiments. Our four protocols
follow this standard explicitly; each has a frozen analysis plan.

---

## 7. Non-Obvious Precedent from Adjacent Fields

**Aviation human factors & dark-cockpit principle** (Billings 1996).
Cockpit design literature on sensory filtering. Inspired our
observation-trimming policy `ledger` (constraint ledger = filtered
state summary). Not cited in ML literature — a contribution to connect
for the paper.

**Chaos engineering circuit-breakers** (Fowler 2014 popularization from
Release It! Nygard 2007). Inspired our recovery policy's circuit-breaker
rule (trip on repeated similar failures).

**Behavioral economics — principal-agent** (Jensen & Meckling 1976).
Framing motivates our "expose budget costs to the agent" recommendation.
Not empirically tested in this program; noted as a conceptual inspiration
for the budget-adaptive protocol.

**Psychophysics — Just Noticeable Difference** (Fechner 1860; Stevens 1957).
Inspires the context-rot JND measurement approach (Gemini's brainstorm
contribution). Not in current protocol; noted as a Tier-3 follow-up.

**Calibration in clinical prediction** (Van Calster et al. 2019, JCE).
Clinical prediction-model calibration methodology (reliability diagrams,
Brier scores, discrimination) directly transferred to our verifier
calibration procedure. This is unusual in ML agent papers — most use
accuracy alone.

---

## 8. Gaps This Program Addresses

| Gap | Addressed by |
|-----|--------------|
| No published factorial isolating verifier calibration from verifier strength | `02-verifier-calibration-protocol.md` |
| No explicit test of scaffolding shadow | `07-scaffolding-shadow-protocol.md` + verifier protocol's IV2 |
| No controlled memory write-policy factorial | `08-memory-write-policy-protocol.md` |
| No adaptive-budget benchmark isolation | `09-budget-adaptive-protocol.md` |
| No standardized harness reporting | `10-harness-card-template.md` |
| No inter-rater-validated failure-mode taxonomy | `11-failure-taxonomy-codebook.md` |

---

## 9. Out-of-Scope (for this research program)

- **Multi-agent harnesses** (agent teams, orchestration). Harness Card v1.0 is
  single-agent. v2.0 extension left for follow-up.
- **Safety-specific scaffolding** (constitutional AI, RLHF-style guards).
  Adjacent field with its own literature.
- **Non-English / non-Python task domains.** Protocols are English + Python-focused.
- **Online / live-web harnesses.** BrowseComp is the closest; full online
  reproducibility requires Wayback Machine / fixed-time snapshots.

---

## 10. Anticipated Reviewer Concerns

**"The experiments are too expensive."**
$53k for the verifier protocol, ~$28k each for the others. Total program:
$150-170k. Comparable to a single graduate student year of GPU compute; cheaper
than many LLM pretraining ablations.

**"Why not just use an existing benchmark's leaderboard data?"**
Leaderboard entries typically don't report harness details, don't fix random
seeds, don't match budget. Our pre-registered design is the minimum for
causal harness claims.

**"You're testing Claude — what about GPT-class models?"**
A cross-family replication is a clear follow-up; pre-registered but not
included in the first round. Budget-constrained choice to get high-resolution
within-family data first.

**"Harness Cards are paperwork."**
Addressed in `10-harness-card-template.md` §Objections and Responses.
