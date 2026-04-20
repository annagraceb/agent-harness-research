# Paper Outline — Working Title

**Scaffolding Shadow: How Harness Design, Not Just Model Capability, Determines Agent Performance**

*(Alternative titles: "The Harness Is the Model: A Scientific Study of Agent-Scaffold Design" / "Beyond Model Cards: Why Agent Benchmark Scores Need Harness Cards")*

---

## Target Venue

**Primary:** NeurIPS 2026 (main track). Agents & Tool Use area is expanding. Pre-registration framing aligns with increasing methodological rigor in ML.
**Secondary:** ICML 2026 Agent4All workshop (for Harness Card standardization paper if split out).
**Tertiary:** arXiv + blog writeup regardless of venue outcome.

---

## Abstract (target 200 words)

> Agent-harness design — the scaffolding around a base LLM that manages tools, context, memory, verification, budget, permissions, and recovery — is increasingly the dominant contributor to agent performance on benchmarks like SWE-bench and OSWorld. Yet published results rarely control for harness variables, treating scaffolding as a nuisance rather than the independent variable it has become.
>
> We introduce **Harness Cards**, a lightweight reporting standard for agent experiments, and present a pre-registered four-experiment program that isolates harness dimensions against model-tier factorials to test the **scaffolding shadow** hypothesis — that harness-induced performance losses grow with model capability.
>
> In the primary experiment, a 4 × 3 factorial on SWE-bench Verified (N = 27,000 rollouts) separates verifier *strength* from verifier *calibration*. We find [result]. Three companion protocols (context-policy, memory write-policy, adaptive budget) test the shadow hypothesis through independent harness dimensions.
>
> Across experiments, [headline finding]. We show that [key result]. The practical implication: at current model capabilities, harness engineering offers performance improvements comparable to a full model-tier jump, at a fraction of the cost. We release all trajectories, code, Harness Cards, and a 12-pattern failure-mode coding rubric to support replication.

*(Result placeholders to be filled after data collection.)*

---

## Paper Structure

### 1. Introduction (~1.5 pages)

**Hook.** The OSWorld gap: humans 72%, agents 12% on identical environments. No plausible path for a 60pp model-capability gain in 2026; most of the gap must be scaffolding.

**Thesis.** "The harness is the model now." When scaffold quality dominates benchmark variance, comparing benchmark scores across papers is comparing harnesses, not models. The field needs:
1. A reporting standard (Harness Card).
2. Controlled experiments isolating harness dimensions.
3. Direct empirical testing of the scaffolding-shadow hypothesis.

**Contributions** (bulleted):
- First factorial separating verifier strength from verifier calibration.
- First direct test of scaffolding shadow across multiple harness dimensions (D1 context, D3 memory, D4 verifier, D5 budget).
- Harness Card v1.0 proposal with reference implementation and validator.
- 12-pattern failure-mode coding rubric with inter-rater validation protocol.
- Runnable toy simulator demonstrating the methodology; revealed a design flaw in the original H1 that pre-registration caught before data collection (novel demonstration of pre-registration value in ML).

### 2. Related Work (~1 page)

Section structure pulled directly from `12-related-work.md`:

- §2.1 Foundational agent architectures (ReAct, Reflexion, Voyager).
- §2.2 Benchmarks stressing harness quality (SWE-bench, SWE-agent, τ-bench, OSWorld, BrowseComp, MLE-bench).
- §2.3 Context management (Lost-in-the-Middle, Context Rot).
- §2.4 Verification and self-criticism (Self-Refine, Tree of Thoughts, LLM calibration).
- §2.5 Industry synthesis (Anthropic Building Effective Agents, Operator, Devin post-mortems).
- §2.6 Methodology: Model Cards, Datasheets, pre-registration in ML.

### 3. The Harness Card Standard (~1 page + full spec in appendix)

- §3.1 Motivation: the uninterpretable-score problem.
- §3.2 Required fields (summary table, full spec in Appendix A).
- §3.3 Validation rules and canonical JSON serialization.
- §3.4 Adoption path (workshop → reference implementation → benchmark requirement).

### 4. Method: The Four-Protocol Program (~2 pages)

- §4.1 Shared design principles: pre-registered, model-tier factorial, held-fixed harness dimensions.
- §4.2 Four protocols at a glance (table).
- §4.3 Shared measurement instruments (pass@1, pass^3, Brier, cost-to-solve, failure-mode tags).
- §4.4 The 12-pattern failure taxonomy (summary; full rubric in Appendix B).
- §4.5 Power analysis methodology (Monte-Carlo simulation; why classical formulas fail for proportions near 0 or 1).

### 5. Experiment 1 — Verifier Calibration × Model Tier (~3 pages)

- §5.1 Design (pull from `02-verifier-calibration-protocol.md`).
- §5.2 Verifier variants V0-V3 (§ from `05-verifier-variants.md`).
- §5.3 Calibration procedure (temperature scaling, threshold selection).
- §5.4 Results
  - Headline table: 4 × 3 pass@1 with 95% CIs.
  - Second table: pass^3.
  - Third table: Brier scores per cell.
  - Figure 1: reliability diagrams per variant per tier.
  - Figure 2: hypothesis test summary with bootstrap CIs.
- §5.5 Discussion
  - H1 (pairwise): supported / rejected with what effect size.
  - H1' (paired-strength, added post-simulation): status.
  - H2 (scaffolding shadow): supported / rejected, magnitude.
  - H3 (reliability sensitivity, exploratory): direction, implication for pass^k use.

### 6. Experiment 2 — Context Policy × Model Tier (~2.5 pages)

- §6.1 Design (`07-scaffolding-shadow-protocol.md`).
- §6.2 Four policies C0-C3 (no-trim, FIFO, ledger, semantic).
- §6.3 Context-rot detection rubric (novel methodology section).
- §6.4 Results
  - Headline 4 × 3 table.
  - Figure 3: context-rot rate vs trajectory length per policy × tier.
  - Figure 4: cell-range R(t) across tiers.
- §6.5 Discussion: shadow confirmed via D1? Magnitude comparable to D4 result from Exp 1?

### 7. Experiment 3 — Memory Write-Policy (~2 pages)

- §7.1 Design (`08-memory-write-policy-protocol.md`).
- §7.2 Four write-policies (none, write-all, salience, utility).
- §7.3 Longitudinal 50-task sequence; memory pollution operationalization.
- §7.4 Results
  - Figure 5: pass@1 trajectory over task index per policy.
  - Figure 6: memory pool size over time.
- §7.5 Discussion: does "memory pollution" exist? Does utility-gating dominate salience-gating?

### 8. Experiment 4 — Adaptive Budget (~2 pages)

- §8.1 Design (`09-budget-adaptive-protocol.md`).
- §8.2 Phase-detection methodology (self-declared vs oracle).
- §8.3 Results
  - Table: pass@1 per arm on BrowseComp.
  - Figure 7: budget consumption curves per arm.
  - Figure 8: phase-agreement matrix (B2 vs B3).
- §8.4 Discussion: can LLMs self-declare phase? Does phase-awareness help?

### 9. Cross-Protocol Meta-Analysis (~1 page)

- §9.1 Per-tier scaffolding-shadow gradient across 4 dimensions.
- §9.2 Failure-mode distribution shifts per protocol.
- §9.3 Conclusion: is scaffolding shadow a general property of agent harnesses?
  - Figure 9: scaffold-shadow fingerprint — one plot summarizing all 4 dimensions.

### 10. The Pre-registration Pivot (~0.5 page, a methodology highlight)

Dedicated box discussing the H1 → H1' refinement that came from the toy simulator. This is a methodological contribution: demonstrating that pre-registration + simulation-before-data catches bugs no amount of peer review would.

### 11. Limitations and Future Work (~1 page)

- Single-model-family (Claude only); cross-family replication pre-registered for follow-up.
- Single-agent only; multi-agent harnesses out of scope.
- Online-web reproducibility constraints in Experiment 4.
- Harness Card v1.0 covers 7 dimensions; extensions for multi-agent orchestration planned.

### 12. Discussion and Conclusion (~1 page)

- The practical implication: harness engineering is a first-class research area, not an engineering detail.
- The methodological implication: agent papers without Harness Cards are not replicable; community should adopt.
- The theoretical implication: scaffolding shadow tells us something about how LLM capability translates into agentic performance — capability is necessary but harness is the amplifier.

### Appendices

- **Appendix A** — Full Harness Card v1.0 spec (pulled from `10-harness-card-template.md`).
- **Appendix B** — 12-pattern failure-mode coding rubric (pulled from `11-failure-taxonomy-codebook.md`).
- **Appendix C** — Power analysis full results tables (from `03-power-analysis.md`).
- **Appendix D** — Pre-registration documents (frozen versions of protocols 02, 07, 08, 09).
- **Appendix E** — Statistical analysis plan (`06-statistical-analysis-plan.md`).
- **Appendix F** — Toy simulator code + full output (`13-eval-simulator-toy.py`).
- **Appendix G** — Harness Cards for each experiment cell (machine-readable YAML).

---

## Target Length

- Main paper: ~18-20 pages.
- With appendices: ~40-50 pages (arXiv version); appendices truncated for conference submission if required.

---

## Figures and Tables — Full List

### Tables (in main text)
- T1: Harness Card fields summary (§3).
- T2: Four protocols overview (§4).
- T3: Experiment 1 headline — 4×3 pass@1 with CIs.
- T4: Experiment 1 — pass^3.
- T5: Experiment 1 — Brier per cell.
- T6: Experiment 2 headline.
- T7: Experiment 3 memory-policy summary.
- T8: Experiment 4 budget-policy summary.
- T9: Cross-protocol scaffolding-shadow gradient.

### Figures
- F1: Reliability diagrams (Exp 1).
- F2: Hypothesis test summary with CIs (Exp 1).
- F3: Context rot vs length (Exp 2).
- F4: Cell range R(tier) per policy (Exp 2).
- F5: pass@1 over longitudinal task index (Exp 3).
- F6: Memory pool size over time (Exp 3).
- F7: Budget consumption curves (Exp 4).
- F8: Phase-agreement matrix (Exp 4).
- F9: Cross-protocol shadow fingerprint (§9).
- F10: Failure-mode distribution shifts per protocol (discussion).

---

## Author Contributions (placeholder)

- **Anna Grace Bentley** — conceptualization, experimental design, protocol pre-registration, Harness Card specification, writing.
- *To be filled: data collection, analysis, auxiliary writing.*

---

## Acknowledgments (placeholder)

- Multi-AI brainstorm that shaped the research program (Claude Opus 4.7, Codex / GPT-5.4, Gemini 3.1 Pro Preview).
- Prior work from Princeton SWE-agent team, τ-bench team, OpenAI evaluation teams whose benchmarks enabled this study.

---

## Submission Checklist (pre-submission)

- [ ] All Harness Cards frozen and hash-validated.
- [ ] Pre-registration documents posted to OSF with timestamps.
- [ ] Trajectories and verifier outputs released under Apache-2.0.
- [ ] Analysis code released; smoke test passes in reviewer-accessible environment.
- [ ] Compute cost transparency statement (total $, cloud-provider details).
- [ ] Ethical statement: no human subjects; agent actions constrained to sandboxed environments.
- [ ] Broader impact section: scaffolding research could be dual-use (better scaffolds for beneficial agents, but also for misaligned agents). Addressed in discussion.

---

## Timeline to Submission

| Milestone | Target Date |
|-----------|-------------|
| Pilot complete (50 tasks, 3 cells) | 2026-05-01 |
| H1' primary/exploratory decision frozen | 2026-05-03 |
| Experiment 1 full data collection | 2026-05-22 |
| Experiment 1 analysis complete | 2026-06-05 |
| Experiments 2-4 data collection (parallel) | 2026-06-30 |
| Cross-protocol meta-analysis | 2026-07-07 |
| First full draft | 2026-07-21 |
| Internal review + revisions | 2026-08-04 |
| **NeurIPS submission deadline (typical: ~May-June 2026)** | Missed for NeurIPS 2026 — retarget ICLR 2027 or arXiv + journal |

**Realistic first-venue target:** ICLR 2027 (typical deadline late September 2026) OR arXiv preprint + direct submission to TMLR.

---

## Blog / Thread Angle (for outreach)

- Single-thread tweet: "We spent 8 weeks proving that the thing you think is 'prompt engineering' is actually a scientific discipline with its own failure modes. Here's what we found — [result thread]."
- Blog post: "Why Your Agent Benchmark Score Is Uninterpretable (And What To Do About It)."
- The toy-simulator-caught-a-bug story is its own short post: "How we almost shipped a failed experiment, and what saved us."
