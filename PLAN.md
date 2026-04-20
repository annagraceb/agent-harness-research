# Agent Harness Research — 8-Hour Autonomous Iteration

**Owner:** Claude (autonomous session)
**User:** Anna Grace Bentley
**Start:** 2026-04-20T07:13Z (2026-04-20T00:13 PDT)
**Deadline:** 2026-04-20T15:15Z (2026-04-20T08:15 PDT)
**Topic:** Scientific study of agent harnesses — what matters, why things go wrong, how to prevent them, how to test this empirically.

## Directive

Iterate autonomously. Use judgment. Stop at deadline. Produce concrete research artifacts that advance the research program outlined in the prior brainstorm's literature map.

## Context

Source material: Team brainstorm (Codex + Gemini + Claude) + literature map delivered in the prior turn. Key outputs to build on:

- 7-dimension harness decomposition (D1-D7)
- 12-pattern failure taxonomy (context rot, tool thrash, plan-execution drift, recovery blindness, rubber-stamp verification, instruction bleed, confidence inversion, scaffolding shadow, memory pollution, budget myopia, permission learned-helplessness, observation collapse)
- 6 paradoxes with falsifiable predictions
- Study coverage matrix identifying gaps in D3-D7
- 9 ranked research gaps (Tier 1 = verifier calibration, scaffolding shadow, adaptive budget, memory write-policy)
- Recommended entry experiment: verifier-calibration × model-tier factorial on SWE-bench Verified

## Iteration Schedule (target: 8 ticks, ~60 min each)

| Tick | Target Artifact(s) | Status |
|------|--------------------|--------|
| T1 | `PLAN.md`, `01-literature-map.md`, `02-verifier-calibration-protocol.md` | done (2026-04-20T07:20Z) |
| T2 | `03-power-analysis.py` + `.md`, `04-harness-schema.py` | done (2026-04-20T07:40Z) |
| T3 | `05-verifier-variants.md`, `06-statistical-analysis-plan.md` | done (2026-04-20T07:50Z) |
| T4 | `07-scaffolding-shadow-protocol.md` | done (2026-04-20T08:05Z) |
| T5 | `08-memory-write-policy-protocol.md`, `09-budget-adaptive-protocol.md` | done (2026-04-20T08:12Z) |
| T6 | `10-harness-card-template.md`, `11-failure-taxonomy-codebook.md` | done (2026-04-20T08:17Z) |
| T7 | `12-related-work.md`, `13-eval-simulator-toy.py` | done (2026-04-20T08:30Z) — sim revealed H1' need; protocol + SAP updated |
| T8 | `14-handoff-summary.md`, polish + index | done (2026-04-20T08:32Z) — core deliverables complete |
| T9 | `15-paper-outline.md` — working title, abstract draft, full section-by-section outline, fig/table list, timeline | done (2026-04-20T09:03Z) |
| T10 | `16-audit-log.md` — consistency audit: 8 bugs found, 8 fixed; cross-file invariants established | done (2026-04-20T09:18Z) |
| T11 | `17-sim-parameter-sweep.py` + `18-sim-sweep-findings.md` — empirical H1 vs H1' regime map | done (2026-04-20T09:25Z) |
| T12 | AgentLoop.run() concrete implementation in `04-harness-schema.py` with deterministic LLM/Oracle/Verifier stubs; end-to-end smoke test passes (4 turns, 10 steps, verifier + oracle both agree) | done (2026-04-20T09:55Z) |
| T13 | `19-meta-analysis-protocol.md` — cross-dimensional meta-analysis: 3 primary meta-hypotheses, 3-panel shadow fingerprint figure, statistical framework (DerSimonian-Laird + bootstrap), publishable-regardless-of-outcome matrix | done (2026-04-20T10:45Z) |
| T14 | `20-asymmetric-miscalibration-sweep.py` + `21-asymmetric-findings.md` — asymmetric miscal shows H1' can fail under realistic LLM patterns; **Brier score must be primary DV, not pass@1** | done (2026-04-20T10:55Z) |
| T15 | `README.md` (directory front-door) + `14-handoff-summary.md` refresh covering T9-T14 additions | done (2026-04-20T11:35Z) |
| T16 | Validation sweep (all 5 scripts OK); consistency fix (§2.1b→§2.1a in protocol); `22-meta-analysis-stub.py` runnable meta-analysis reference with 3-panel figure + JSON output | done (2026-04-20T12:25Z) |
| T17 | `23-executive-summary.md` (one-page stakeholder doc); handoff's Monday-actions list; memory → COMPLETED | done (2026-04-20T13:15Z) |
| T18 | User pushback on $140k → `24-budget-sensitivity-simulation.py` + `25-budget-sweet-spot.md` — **$30k sweet spot answers all 3 primary hypotheses; $77k for full program**. Exec summary updated. | done (2026-04-20T13:45Z) |
| — | Session complete. Remaining time: buffer. | — |

## Rules for Future Ticks

1. Read `PLAN.md` first. Do the next `pending` artifact.
2. Mark artifact `done` on completion with a one-line note.
3. Check time budget. If <30 minutes remain, skip to Tick 8 (handoff).
4. If artifact exceeds 60 min, split and update plan.
5. No placeholder content. Every artifact must be self-sufficient research output.
6. When scheduling next wakeup: stay within 1800-2400s (30-40 min) to balance progress vs. cache efficiency. ≥300s < delay < 2700s to avoid cache-miss edge cases.
7. Stop iterating at deadline: produce final handoff even if artifacts incomplete.

## Artifact Index (auto-updated)

- `01-literature-map.md` — 7-dimension harness decomp, 12-pattern failure taxonomy, 9 ranked gaps
- `02-verifier-calibration-protocol.md` — full pre-registration for verifier-calibration × model-tier factorial on SWE-bench Verified, with Harness Card v0.1
- `03-power-analysis.py` + `03-power-analysis.md` — Monte-Carlo power sim; recommends N=750 per cell (revised up from 500 after actual output disagreed with priors)
- `04-harness-schema.py` — pydantic-typed Harness Card contract; executable skeleton defining the interface every cell must conform to
- `05-verifier-variants.md` — full operational spec for the 4 verifier conditions (V0-V3) with pre-registered prompts, calibration diagnostics, audit rubric
- `06-statistical-analysis-plan.md` — pre-registered confirmatory and exploratory tests, headline tables, surprise-decision rules
- `07-scaffolding-shadow-protocol.md` — D1 (context-policy) × tier factorial testing shadow hypothesis via a 2nd harness dimension; C0-C3 trimming policies with context-rot detection rubric
- `08-memory-write-policy-protocol.md` — D3 memory longitudinal pre-reg; 4 write-policies over 50 tasks; tests memory pollution and utility-gating hypotheses
- `09-budget-adaptive-protocol.md` — D5 budget pre-reg; phase-aware adaptive allocation vs fixed on BrowseComp; tests budget myopia + phase self-knowledge
- `10-harness-card-template.md` — Harness Card v1.0 standard: 12 required field groups, minimum-viable short-form, validation rules, adoption path
- `11-failure-taxonomy-codebook.md` — coding rubric for 12-pattern taxonomy with decidable criteria per tag; target κ > 0.70
- `12-related-work.md` — literature synthesis; maps prior work onto 7-dim harness taxonomy; identifies this program's contribution vs. each gap
- `13-eval-simulator-toy.py` — runnable end-to-end simulator; produces 4×3 factorial tables, bootstrap CIs, hypothesis-test results. Revealed H1' need — back-ported to protocol + SAP.
- `14-handoff-summary.md` — executive-facing summary: TL;DR, artifact index, scientific findings pre-data, critical path, open questions for user
- `15-paper-outline.md` — full paper outline: working title, 200-word abstract, section-by-section with figure/table list, appendix plan, submission timeline targeting ICLR 2027
- `16-audit-log.md` — cross-file consistency audit: 8 inconsistencies documented and fixed; enum alignments, N=500→N=750 references, Harness Card YAML v1.0 conformance, VerifierSpec nested-calibration refactor; invariants established for future edits
- `17-sim-parameter-sweep.py` + `18-sim-sweep-findings.md` — accuracy-regime sweep; empirical finding that H1' is robust (~80% of cells) while H1 is narrow (~10% of cells); strengthens case for H1' as unconditional primary
- `04-harness-schema.py` (updated) — AgentLoop.run() now concretely implemented; deterministic LLM + tool + oracle + verifier stubs added; end-to-end smoke test runs in __main__ and produces a complete Trajectory
- `19-meta-analysis-protocol.md` — cross-dimensional meta-analysis pre-registration: shadow-fingerprint figure spec, DerSimonian-Laird pooled effects, publishable-regardless matrix, failure-mode-fingerprint predictions per dimension
- `20-asymmetric-miscalibration-sweep.py` + `21-asymmetric-findings.md` — second sim-caught protocol issue: realistic LLM asymmetric miscalibration (over-accept >> over-reject) can render H1' invisible in pass@1; recommends Brier as primary calibration DV; proposes H1'a (Brier) + H1'b (pass@1-transfer) split
- `README.md` — directory front-door with quick-start, artifact table-of-contents, key findings TL;DR
- `22-meta-analysis-stub.py` — runnable reference for the meta-analysis: ingests per-dim rollouts, computes R(t) and shadow gradient γ_d, tests M1-M3, produces `meta_results_synthetic.json` and `shadow_fingerprint_synthetic.png` (3-panel figure)
- `meta_results_synthetic.json` + `shadow_fingerprint_synthetic.png` — stub outputs on 72k synthetic rollouts; demonstrate the analysis pipeline end-to-end
- `23-executive-summary.md` — one-page stakeholder document: problem, program, findings, decision requested, Monday actions. Designed for direct forwarding.
