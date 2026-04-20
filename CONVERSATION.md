# The Story Behind This Directory

*A narrative account of the conversation that produced all of this. Included so
readers can see how the research got shaped — not just what the artifacts say,
but why they exist and what they cost to arrive at.*

---

## The Question

It started with a simple ask:

> "I would like to look at studies that help identify what matters in agent
> harnesses. Why things go wrong, how to prevent them, specifics and
> generalizations. How can I test this scientifically?"

No brief. No budget. Just the open question.

## Phase 1 — The Multi-AI Brainstorm

Rather than answer solo, a Team brainstorm was run across three AIs:

- **Codex** (GPT-5.4 via Codex CLI) — tasked with empirical grounding: find
  specific published studies measuring harness-level variables.
- **Gemini** (3.1 Pro Preview) — tasked with lateral thinking: what analogies
  from adjacent fields (aviation cockpits, chaos engineering, behavioral
  economics) apply?
- **Claude** (Opus 4.7, this assistant) — tasked with pattern-naming: what
  failure modes have no labels yet?

They ran in parallel. Codex returned a grounded citation set (SWE-bench,
τ-bench, SWE-agent's ACI effect, OSWorld's 72% humans vs. 12% agents
gap, Lost-in-the-Middle, Chroma Context Rot, Reflexion, Voyager). Gemini
reframed the problem as "the LLM is a noisy CPU; the harness is the OS"
and proposed three contrarian experiment designs (FSM phase-gating,
AST-based editing, hormonal-urgency prompts). Claude named twelve failure
patterns — context rot, tool thrash, plan-execution drift, recovery
blindness, rubber-stamp verification, instruction bleed, confidence
inversion, scaffolding shadow, memory pollution, budget myopia, permission
learned-helplessness, observation collapse — and raised six paradoxes
(more tools → worse, longer reasoning → more confidently wrong, etc.).

Synthesis: all three agreed on one thing, from three angles —
**scaffolding dominates capability**. Benchmarks like SWE-bench and OSWorld
measure the interaction of model × harness × task, but papers almost never
report harness details.

## Phase 2 — The Literature Map

Asked to go deeper, the session produced:

- A **7-dimension harness decomposition** (observation, action, memory,
  verification, budget, permissions, recovery).
- A **study coverage matrix** showing which published work touches which
  dimension — and which dimensions have essentially no controlled studies.
- **Nine ranked research gaps**, with the top four being Tier-1: verifier
  calibration, scaffolding-shadow test, adaptive budget, memory write-policy.
- A **recommended entry experiment**: 4 × 3 factorial on SWE-bench Verified
  separating verifier strength from verifier calibration.

## Phase 3 — The 8-Hour Autonomous Iteration

Then came an unusual directive:

> "Iterate for the next 8 hours as you best see fit. Do not stop until
> 8:15 AM Pacific Time on April 20, 2026."

Eight hours, no check-ins required, produce concrete research output.

Seventeen ticks (T1-T17) over 8 hours produced the artifacts in this
directory. The rough flow:

- **T1-T3** — Pre-registered the verifier-calibration protocol with a frozen
  analysis plan, built the Monte-Carlo power simulation, specified the four
  verifier variants (V0-V3) and the statistical analysis plan.
- **T4-T5** — Pre-registered three companion protocols (scaffolding shadow
  via context policy, memory write-policy, adaptive budget).
- **T6** — Drafted **Harness Card v1.0** as a reporting standard and the
  **12-pattern failure-mode coding rubric**.
- **T7** — Ran the toy end-to-end simulator. **It caught a protocol flaw**:
  the original H1 conflated verifier strength with calibration. Added
  H1' (paired-strength contrast) as a refined hypothesis.
- **T8** — Initial handoff summary.
- **T9** — Full paper outline with abstract, section-by-section, fig/table
  list, submission timeline.
- **T10** — Consistency audit across 15 files. Found and fixed 8 real bugs
  (stale N=500 references, enum mismatches between schema and spec, YAML
  non-conformance).
- **T11** — Parameter sweep across accuracy regimes. **Second empirical
  finding**: H1 supported in only ~10% of cells; H1' supported in ~80%.
- **T12** — Filled in the concrete `AgentLoop.run()` implementation with
  deterministic stubs. End-to-end smoke test passes.
- **T13** — Cross-dimensional meta-analysis protocol: how to combine the
  four protocols' outputs into a publishable scaffolding-shadow fingerprint.
- **T14** — Asymmetric-miscalibration sweep. **Third empirical finding**:
  under realistic LLM asymmetric miscal, pass@1 is insensitive to
  calibration. H1' split into H1'a (Brier-based) + H1'b (pass@1 transfer).
  Brier elevated to primary DV.
- **T15** — README as directory front-door; handoff summary refresh.
- **T16** — Full directory validation (6 Python scripts pass); runnable
  meta-analysis stub with 3-panel shadow-fingerprint figure.
- **T17** — One-page executive summary and Monday-actions list; final
  sign-off.

By the end: 24 primary artifacts, 6 runnable Python scripts, ~6,000 lines.

## Phase 4 — The Budget Pushback

The initial recommendation called for a **$140k compute budget** — four
protocols at N=750 per cell across three model tiers. The user pushed back:

> "$140k is a lot. Is that all we can really do?"

Fair question. The response was a concrete menu: pilot at $900, Sonnet-only
verifier at $13.5k, two-tier $50k, retrospective verifier on Princeton's
released trajectories at $2-5k.

Then another round of simulation — this time a **budget sensitivity sweep**
testing what each budget level actually buys:

- Under $5k: only the Brier-based hypothesis answerable (workshop paper).
- $10-15k: Sonnet-only, answers calibration but no shadow.
- **$30k: 3-tier at N=423 answers all three primary hypotheses.** The
  scaffolding-shadow paper is fully achievable at this budget.
- $50-77k: same hypotheses with tighter CIs.
- $100-140k: diminishing returns — precision, not new answers.

**The $140k figure had been the ceiling for tight confidence intervals, not
the floor for answering the question.** A 4.7× reduction in budget preserves
all primary-hypothesis answerability.

## Phase 5 — The Actual Budget

The user then said something that reframed everything:

> "I'll be honest. I am a person who budgets what salad dressing they buy.
> I can't afford anything."

So every budget above zero was out of reach. Reframed again.

Three zero-or-near-zero paths were identified:

1. **Methodology paper ($0)** — Publish the Harness Card standard, the
   failure taxonomy, and the pre-registration-caught-two-bugs story as a
   workshop paper or blog post. No experiments required. The contribution
   is real: a reporting standard and methodology the field is missing.

2. **Retrospective verifier analysis ($0-5)** — Princeton released
   SWE-agent trajectories publicly. Add a verifier layer using free-tier
   Gemini or Anthropic's $5 starter credits. Calibrate. Report. Real data,
   no agent-loop cost.

3. **Free local compute ($0)** — Kaggle's free 30 hours/week of GPU can run
   Qwen-2.5-7B on SWE-bench Lite at 50-100 tasks. Proof of concept, not
   powered, but real.

Then the user said:

> "I do have an RTX 3060. Can you do much there? I can spare maybe $50 of
> Anthropic API credits too."

That changed things. A real frugal plan emerged: local Qwen-2.5-Coder-7B
for the *agent* (zero API cost), Claude Haiku 4.5 for the *verifier*
(cheapest Anthropic tier). On HumanEvalFix (easier than SWE-bench,
appropriate for 7B capability), ~$21 of the $50 budget buys 600 full
rollouts with verifier coverage. About 50 hours of GPU time on the 3060.
Real data, H1'a definitively answered, H1'b directionally answered.

## Phase 6 — Publish

> "Can you publish all this to GitHub please? By all of this, I mean the
> entire arc of the conversation, technical basis, all of it."

Which is what you're reading now.

---

## What This Directory Is

Not a finished paper. Not a completed experiment. A **research program
specification**, assembled in one long evening of AI-assisted iteration,
refined through three rounds of feedback, culminating in a path that someone
with a consumer GPU and $50 can actually execute.

The central claim — **scaffolding shadow**, that harness-induced performance
losses grow with model capability — remains untested on real data. The
protocols, the standard, the taxonomy, the methodology demonstration, and
the two sim-caught bugs are all real contributions that exist independently
of whether the hypothesis turns out to be right.

The story of this directory is partially the story of AI-assisted research
as a methodology: tools that let one person spec, simulate, and audit a
complete research program in hours instead of weeks. The findings caught by
simulation before data collection — *twice* — are themselves evidence that
pre-registration plus simulation is a genuinely valuable methodological
discipline for the field.

---

## Credits

- **Lead:** Anna Grace Bentley
- **AI collaborators:** Claude Opus 4.7 (primary writing, pattern-spotting),
  Codex / GPT-5.4 (empirical grounding), Gemini 3.1 Pro Preview (lateral
  analogies)
- **Inspiration:** the agent-research community's collective frustration
  with uninterpretable benchmark scores

---

*Read `README.md` for the quick-start. Read `23-executive-summary.md` for
the one-page stakeholder version. Read `15-paper-outline.md` for the full
paper outline. Read `PLAN.md` for the tick-by-tick activity log.*
