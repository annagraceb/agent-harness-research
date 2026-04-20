# Agent Harness Research — Working Directory

A pre-registered research program studying **what matters in agent harnesses**
— the scaffolding around LLMs that manages tools, context, memory, verification,
budget, permissions, and recovery.

**Status (2026-04-20):** Pre-registration complete. 22 artifacts produced during
an 8-hour autonomous research iteration. No primary data collected yet.

---

## Quick Start

Two runnable Python scripts, no API calls required, < 5 seconds each:

```bash
# End-to-end AgentLoop smoke test (reference implementation)
python3 04-harness-schema.py

# Toy 4×3 factorial simulator (produces headline tables + hypothesis tests)
python3 13-eval-simulator-toy.py

# Parameter sweeps (symmetric and asymmetric miscalibration)
python3 17-sim-parameter-sweep.py
python3 20-asymmetric-miscalibration-sweep.py

# Power analysis (Monte-Carlo)
python3 03-power-analysis.py

# Meta-analysis stub (synthetic — produces shadow_fingerprint_synthetic.png)
python3 22-meta-analysis-stub.py
```

All scripts are deterministic (seed=20260420) and runnable with only
`numpy` + `pydantic` installed.

---

## What's Here — By Purpose

### Start here (for orientation)

| File | Purpose |
|------|---------|
| `23-executive-summary.md` | **One-page stakeholder document** — problem, program, findings, decision requested. Best single entry point. |
| `PLAN.md` | Master plan, tick-by-tick status, artifact index |
| `14-handoff-summary.md` | Longer technical summary: TL;DR, findings, Monday-actions list |
| `15-paper-outline.md` | Full paper outline: abstract draft, section-by-section, fig/table list, submission timeline |

### The four pre-registered experiments (pick one to start)

| File | Dimension | Benchmark | Cost (est.) |
|------|-----------|-----------|:-----------:|
| `02-verifier-calibration-protocol.md` | D4 verification | SWE-bench Verified | ~$53k |
| `07-scaffolding-shadow-protocol.md` | D1 observation (context) | SWE-bench Verified | ~$54k |
| `08-memory-write-policy-protocol.md` | D3 memory | SWE-bench Lite (longitudinal) | ~$2k |
| `09-budget-adaptive-protocol.md` | D5 budget | BrowseComp | ~$29k |

### Foundations

| File | Purpose |
|------|---------|
| `01-literature-map.md` | 7-dim harness decomposition, 12-pattern failure taxonomy, 9 ranked research gaps |
| `12-related-work.md` | Literature synthesis mapping prior work onto the 7 dimensions |

### Standards and rubrics

| File | Purpose |
|------|---------|
| `10-harness-card-template.md` | Harness Card v1.0 reporting standard (spec + validation rules + adoption path) |
| `11-failure-taxonomy-codebook.md` | Decidable criteria for the 12-pattern taxonomy (target κ > 0.70) |

### Statistical methodology

| File | Purpose |
|------|---------|
| `03-power-analysis.md` + `.py` | Monte-Carlo power simulation; recommends N=750 per cell |
| `05-verifier-variants.md` | Operational spec for the 4 verifier conditions (V0-V3) |
| `06-statistical-analysis-plan.md` | Pre-registered confirmatory/exploratory tests, frozen analysis plan |
| `19-meta-analysis-protocol.md` | Cross-protocol meta-analysis pre-reg: shadow fingerprint spec, DerSimonian-Laird pooled effects |

### Reference implementation

| File | Purpose |
|------|---------|
| `04-harness-schema.py` | Pydantic Harness Card + concrete AgentLoop.run() + stubs (LLM, tools, verifier, oracle) |
| `13-eval-simulator-toy.py` | End-to-end 4×3 factorial simulator on synthetic tasks |
| `17-sim-parameter-sweep.py` | Accuracy-regime sweep showing when H1 vs H1' holds |
| `18-sim-sweep-findings.md` | Findings from 17: H1' robust (~80% of cells), H1 narrow (~10%) |
| `20-asymmetric-miscalibration-sweep.py` | Realistic asymmetric-miscal sweep |
| `21-asymmetric-findings.md` | Findings from 20: **Brier must be primary calibration DV** |

### Process artifacts

| File | Purpose |
|------|---------|
| `16-audit-log.md` | Cross-file consistency audit (8 bugs found, 8 fixed) |

---

## Key Findings (Pre-Data)

The 8-hour iteration produced two methodological findings, both caught by
simulation before any real data collection:

### Finding 1 — Sample size correction

Running the Monte-Carlo power simulation (`03-power-analysis.py`) with the
original N=500 per cell revealed only 77% power for the primary hypothesis
at Sonnet tier. **Revised up to N=750** (89% power). H3 was
**reclassified from confirmatory to exploratory** after being shown
irreducibly under-powered at feasible N.

### Finding 2 — Primary DV correction

The symmetric-miscalibration sweep (`17`) showed H1 as originally stated
conflates verifier strength with calibration — leading to H1' (paired-strength
contrast). The asymmetric-miscalibration sweep (`20`) then showed that under
realistic LLM asymmetric miscal, even H1'-on-pass@1 can be null.

**Resolution:** H1' split into:
- **H1'a** — Brier-based calibration validity (primary, near-certain to hold)
- **H1'b** — pass@1 performance transfer (primary only if pilot shows asymmetry ratio < 3x)

Brier score is elevated to **primary DV** for the calibration hypothesis.

---

## Research Program Summary

The four protocols form a coherent program:

```
    D1 context     D3 memory     D4 verification     D5 budget
        |             |                  |                |
        v             v                  v                v
   Protocol 2    Protocol 3        Protocol 1       Protocol 4
   (context-     (memory-          (verifier-       (budget-
    policy)       write-policy)     calibration)     adaptive)
        |             |                  |                |
        +-------------+------------------+----------------+
                                |
                                v
                       Meta-Analysis (Protocol 19)
                        → Scaffolding Shadow Fingerprint
```

**Total program cost:** ~$150-170k over 8-14 weeks.
**Publication target:** single compound paper + meta-analysis supplement.

---

## How This Directory Was Built

These artifacts were produced in an 8-hour autonomous iteration on 2026-04-20
following a multi-AI brainstorm (Codex + Gemini + Claude) that produced the
initial literature map. See `PLAN.md` for the tick-by-tick activity log.

Every artifact is self-sufficient; `PLAN.md` is the master index. Start at
`14-handoff-summary.md` for the executive view, then dive into the protocol
that matches your interest.

---

## For Reviewers / Collaborators

- **Pre-registration:** All four protocols are ready to freeze on OSF once a
  pilot is run (Week 1 of the timeline in `15-paper-outline.md`).
- **Replication:** Harness Card v1.0 attached to every cell. Trajectories
  and verifier outputs to be released under Apache-2.0 at publication.
- **Open questions:** See `14-handoff-summary.md` §"Open Questions for User Review."

---

## License

All materials in this directory: Apache-2.0 upon publication. Current state:
internal, pre-publication.

## Contact

Primary: Anna Grace Bentley
