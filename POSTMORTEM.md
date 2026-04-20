# Postmortem

*Added 2026-04-20 after adversarial review. This document supersedes the
triumphalist framing in the original 14-handoff-summary.md and 23-executive-
summary.md. If this file disagrees with those, this file wins.*

---

## What I claimed

The repo was built around a hypothesis called "scaffolding shadow":
harness-induced performance losses *grow* with model capability. Four
pre-registered experiments were proposed to test it. A Harness Card v1.0
reporting standard, a 12-pattern failure taxonomy, and a runnable agent
loop were built as supporting infrastructure. A frugal $21 execution path
on an RTX 3060 + $50 of Anthropic credits was pitched as a viable way to
produce real evidence.

## What three independent critics found

After the repo went public, I dispatched three critical reviewers —
methodological (Codex/GPT-5.4), community-lens (Gemini 3.1 Pro), and
devil's-advocate (Claude Opus 4.7). Their reviews converged on four
structural problems.

### 1. The scaffolding-shadow claim is weakly falsifiable.

The decision rule in `19-meta-analysis-protocol.md` leaves interpretive
oxygen at every outcome. 3/4 dimensions positive → supported. 2/4 →
"dimension-specific." 0/4 → "wait for stronger models." A claim that no
possible data kills isn't a claim.

### 2. The H1 → H1' → H1'a + H1'b hypothesis ladder is forking paths.

Each time simulation flagged a problem with the primary hypothesis, the
primary got renamed. The end state (H1'a on Brier) is mathematically
guaranteed true — temperature scaling minimizes Brier by construction —
so the "primary hypothesis" can't fail. That's retreat labeled as
refinement.

### 3. The frugal plan cannot test the headline claim.

Single model family, single tier (Qwen-7B), single benchmark
(HumanEvalFix), mostly single seed. A claim about interaction with
capability requires *multiple capability levels*. The $21 plan tests
pipeline viability and the verifier's Brier improvement; it does not
test the central interaction claim. I kept the headline and shrank the
design until they no longer matched.

### 4. "Simulation caught two bugs" is standard practice inflated.

Catching N=500 underpowering is what power analysis *is*. Catching an
insensitive DV is what simulation *is for*. Calling the tools' normal
operation "methodology contributions" is grade inflation. A field with
50 years of this practice (medicine) wouldn't publish "our power
analysis correctly sized the sample."

---

## The honest diagnosis

Stripped of framing, the substantive content of the program was:

> **What you do (your harness) matters.**

That's true, has been known since the 2024 Princeton SWE-agent paper, and
is the foundation the program quietly rested on. The *non-tautological*
claim — that the effect **interacts with capability** — is the only
genuinely novel hypothesis, and my design can't test it.

The apparatus (pre-registration, simulation, taxonomies, Harness Card) is
all real work. It just doesn't fix the claim-to-evidence mismatch. It
dressed up a small tractable claim in infrastructure built for a larger
untractable one.

---

## What this repo actually is, honestly

Three publishable artifacts, each narrower than the original pitch:

### A — A taxonomy and standards paper
Harness Card v1.0 + the 12-pattern failure codebook + the reference
`AgentLoop` implementation. Workshop-tier contribution: a shared
vocabulary and an optional reporting format. Not a scientific finding;
an organizational one. Cost: $0.

### B — A frugal single-tier measurement
Qwen-2.5-Coder-7B on HumanEvalFix, V0 condition, 22/50 = 44% pass,
Wilson 95% CI [31%, 58%]. Runnable and reproducible. One clean data
point on "scaffolding matters at small scale" — does not generalize
and does not attempt to. Cost: $0 (local).

### C — A methodology-failure essay
The honest narrative: an 8-hour AI-assisted session produced a research
program whose headline claim outran the evidence it could gather; three
independent critics surfaced that in about 2,000 tokens; the author
pivoted. Cost: already incurred; writing cost only.

None of (A), (B), (C) claims scaffolding shadow.

---

## What the headline "scaffolding shadow" claim would require

For future reference, so I don't re-confuse what would actually test it:

- Cross-tier data: at least 3 distinct capability levels.
- Cross-family data: at least 2 model families (Anthropic + one other).
- Held-out prompt-validation set (so pass rates aren't tuned on the
  same distribution they're scored on).
- A negative-control scaffold dimension pre-specified to *not* interact
  with tier (so positive interactions can't be confused with generic
  capability effects).
- Pre-registered falsifier: a specific quantitative outcome that would
  make me accept "shadow hypothesis rejected."
- Blinded analysis: condition labels replaced with arbitrary IDs during
  analysis.

Estimated floor cost to do this cleanly: ~$30k (per
`25-budget-sweet-spot.md`), which I cannot afford. Absent those
resources, the claim remains an open hypothesis, not a finding.

---

## What stays, what goes, what gets reframed

**Stays in the repo as-is (infrastructure is real):**
- `04-harness-schema.py` (reference implementation, runs)
- `10-harness-card-template.md` (spec, reframed as reviewer-enforced
  replicability requirement per Gemini critic, not a lab-adoption
  proposal)
- `11-failure-taxonomy-codebook.md` (with acknowledged ontological
  messiness per Codex critic)
- `27-ollama-adapter.py`, `28-frugal-runtime.py`, `29-haiku-verifier.py`
  (tooling; works)
- `30-v0-baseline-results.md` (honest data point)

**Reframed (no longer makes interaction claim):**
- `02-verifier-calibration-protocol.md` — treat as a single-tier
  calibration study, not a shadow test
- `07-scaffolding-shadow-protocol.md` — rename and rescope, or mark as
  "deferred until cross-tier budget available"
- `19-meta-analysis-protocol.md` — only runs if all four protocols
  eventually have real data, which is not the current plan
- `23-executive-summary.md` — will be rewritten to match this postmortem

**Delete from any paper submission:**
- `CONVERSATION.md` (production metadata; invites skepticism)
- Tick logs and effort narration in `14-handoff-summary.md`
- The `PLAN.md` history view
- Any "publishable regardless of outcome" language

---

## The lesson in one line

**I built infrastructure for a science I couldn't do, then dressed the
infrastructure as the science.** The infrastructure is useful on its own
terms; the science requires what I don't have.

---

## References

- Full critic round: three independent reviews from Codex, Gemini, and a
  Claude devil's-advocate agent, dispatched 2026-04-20. Convergence on
  the four failure modes above.
- Generalized learnings, diagnostic questions, and prevention checklist:
  https://github.com/annagraceb/learnings/blob/main/001-agent-harness-research.md
- Original documents being superseded: `14-handoff-summary.md`,
  `23-executive-summary.md`. Those documents still reflect the
  pre-critic framing; they are kept for transparency but this postmortem
  is the correct current read.

---

## One question for future me

When starting the next project, before writing anything:

> **"What would have to be different about the world for me to abandon
> this claim?"**

If I can't answer that in one sentence, I don't have a claim yet.
