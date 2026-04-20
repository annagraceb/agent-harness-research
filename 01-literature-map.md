# Literature Map: Agent Harness Research

*Snapshot of the Team brainstorm's literature map, preserved verbatim as the foundation artifact for subsequent protocols.*

## A. Harness Decomposition — Seven Dimensions

| # | Dimension | What it controls | Failure signature |
|---|-----------|------------------|-------------------|
| D1 | **Observation quality** | What the agent sees after a tool call | Context rot, observation collapse |
| D2 | **Action affordances** | Tool schema, granularity, phase-gating | Tool thrash, tool confusion |
| D3 | **Memory policy** | What persists across turns; write/retrieve gating | Memory pollution, instruction bleed |
| D4 | **Verification strength** | Self-check, test oracle, judge quality | Rubber-stamp verification, reward hacking |
| D5 | **Budget allocation** | Token/step/cost spending policy | Budget myopia, loop traps |
| D6 | **Permission model** | Capability tiers, destructive-op gating | Permission learned-helplessness, irreversible errors |
| D7 | **Recovery policy** | Detecting off-track and replanning | Recovery blindness, plan-execution drift |

## B. Study Coverage Matrix

| Study | D1 | D2 | D3 | D4 | D5 | D6 | D7 |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| ReAct (Yao+ 2022) | ○ | ● | | | | | ○ |
| Reflexion (Shinn+ 2023) | | | ● | ● | | | ● |
| Voyager (Wang+ 2023) | | ○ | ● | | | | ○ |
| SWE-bench (Jimenez+ 2023) | ○ | ○ | | ○ | | | |
| SWE-agent (Yang+ 2024) | ● | ● | | ○ | | | ○ |
| τ-bench (Yao+ 2024) | ○ | ● | | ● | | ● | ○ |
| AgentBench (Liu+ 2023) | ○ | ○ | | | | | ○ |
| WebArena (Zhou+ 2023) | ● | ● | | | | | ○ |
| OSWorld (Xie+ 2024) | ● | ● | | | | ○ | ○ |
| BrowseComp (OpenAI 2025) | ○ | | ○ | ○ | ● | | |
| MLE-bench (OpenAI 2024) | | ○ | | ○ | ● | | ○ |
| Lost-in-the-Middle (Liu+ 2023) | ● | | | | | | |
| Chroma Context Rot (2024) | ● | | ○ | | | | |
| METR time-horizons (2024-25) | | | | | ● | | ○ |
| Anthropic Building Effective Agents (2024) | ○ | ● | ○ | ○ | ○ | | ○ |
| Princeton SWE-agent (2024) | ● | ● | | | | | |

## C. Named Failure Patterns (Claude's vocabulary contribution)

1. **Context rot** — global coherence decay distinct from retrieval loss
2. **Tool thrash** — oscillation without state progress
3. **Plan-execution drift** — plan still cited but no longer describing behavior
4. **Recovery blindness** — agents don't detect off-track state
5. **Rubber-stamp verification** — verifier returns "looks good" regardless
6. **Instruction bleed** — system-prompt instructions silently weaken by turn N
7. **Confidence inversion** — higher stated confidence → lower correctness
8. **Scaffolding shadow** — harness bugs only stronger models expose
9. **Memory pollution** — writes triggered by salience, not utility
10. **Budget myopia** — uniform spending instead of phase-aware
11. **Permission learned-helplessness** — after one denial, stops attempting variants
12. **Observation collapse** — multi-page outputs summarized into one sentence that loses key detail

## D. Six Paradoxes with Predictions

1. More tools → worse performance (inverted-U on τ-bench, τ-bench/ToolBench signal)
2. Longer reasoning → more confidently wrong (CoT hardening)
3. Better memory → worse recall (retrieval noise beats signal)
4. Stronger base model → more harness bugs (scaffolding shadow)
5. Explicit planning → lower success on short tasks (planning overhead > benefit)
6. Verifier added → accuracy drops (miscalibrated verifier rejects correct trajectories)

## E. Nine Ranked Research Gaps

**Tier 1 (high leverage, tractable today):**
1. Verifier calibration as an IV — swap strength and calibration independently
2. Scaffolding × model-tier factorial — directly tests scaffolding shadow
3. Adaptive vs. fixed budget — existing benchmarks have the knobs
4. Memory write-policy factorial — salience-gated vs. utility-gated

**Tier 2 (high leverage, infrastructure cost):**
5. Harness Card reporting standard — meta-contribution
6. Permission-tier ablation — requires adversarial hidden-task generator

**Tier 3 (novel, methodologically risky):**
7. Context-rot JND psychophysics — per-model, per-task-type thresholds
8. FSM phase-gated harness study — tests Paradox of Choice
9. Recovery-rate as primary DV — re-analyze public trajectory logs

## F. Key Measurement Instruments

- `pass@k`, `pass^k` (reliability; τ-bench innovation)
- Cost-to-solve, steps-to-solve
- Invalid-tool-call rate, recovery-rate-after-error
- Position-sensitivity curves, time-horizon (50% success)
- Brier/ECE for verifier calibration (unused in current lit)
- Scaffold-capability interaction effect size (unused)

## G. Recommended Entry Experiment

**Verifier-calibration × model-tier factorial on SWE-bench Verified.**

- IV1: verifier ∈ {none, weak-calibrated, strong-uncalibrated, strong-calibrated}
- IV2: model tier ∈ {Haiku 4.5, Sonnet 4.6, Opus 4.7}
- DV1: pass@1 (750 tasks per cell; revised up from 500 after power analysis — see `03-power-analysis.md`)
- DV2: pass^3 (reliability)
- DV3: verifier Brier score (calibration itself)
- DV4: actions-to-solve (efficiency)

Predictions: (a) weak-cal > strong-uncal; (b) scaffolding-shadow interaction at top tier; (c) pass^3 separates arms more than pass@1.

## H. Provenance

Generated in a multi-AI Team brainstorm using:
- 🔴 Codex CLI (gpt-5.4) — empirical grounding with citations
- 🟡 Gemini CLI (gemini-3.1-pro-preview) — lateral/cross-disciplinary framings
- 🔵 Claude (Opus 4.7) — pattern naming and synthesis

Session artifacts preserved in this directory.
