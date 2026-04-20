# Verifier Variants — Detailed Specification

*Operational definitions for the four verifier conditions in the factorial.
Each variant is a fully-specified module so that "swap the verifier" is a
single configuration change, not a design change.*

## Variant index

| Variant | Model | Calibration | Threshold | Purpose |
|---------|-------|-------------|-----------|---------|
| V0 `none`               | — | — | — | Baseline: no verifier |
| V1 `weak-calibrated`    | Claude Haiku 4.5 | temperature-scaled | cost-optimal | Tests: can a cheap but calibrated verifier beat a strong uncalibrated one? |
| V2 `strong-uncalibrated`| Claude Opus 4.7 | raw | 0.5 | The "just add GPT-4-judge" current practice |
| V3 `strong-calibrated`  | Claude Opus 4.7 | temperature-scaled | cost-optimal | Upper bound on verifier value |

## V0: No Verifier (baseline)

Agent runs the base ReAct loop. On termination the final diff is accepted as-is.
No extra inference is performed. This is the pure-capability baseline.

**What this arm measures:** the *marginal* value of verification — does any verifier
help at all, given a well-designed base loop?

**Cost:** zero verifier compute, one rollout per task.

## V1: Weak Calibrated (Claude Haiku 4.5 judge)

**Judge model:** Claude Haiku 4.5. Chosen because it is cheap (~$0.80/M input tokens,
~$4/M output tokens as of 2026-01) and capability-distinguished from the base agent
model. Using the same model as judge as base would confound "verifier quality" with
"second-sample reliability."

**Prompt (pre-registered):**

```
You are reviewing an agent's attempt to solve a software-engineering task.

TASK
{task_description}

TRAJECTORY (compressed)
{trajectory_compressed}

PROPOSED DIFF
{final_diff}

Respond as strict JSON with fields:
  correct: boolean — does this diff implement the task correctly?
  confidence: float in [0,1] — probability the diff passes the hidden test suite
  reasoning: string ≤ 200 words — why you believe this

Strictness: only answer "correct: true" if the diff addresses the stated task and
you would predict it to pass an independent test. Err on the side of rejection only
if there is clear evidence of incorrectness — otherwise use your confidence to reflect
uncertainty.
```

**Trajectory compression:** before passing to the judge we:
1. Drop all `THINK` steps (save one final plan summary).
2. Keep all `TOOL_CALL` args.
3. Truncate `TOOL_RESULT` to 500 tokens each (head + tail, middle ellipsed).
4. Keep all failed `run_tests` outputs in full.
5. Always keep final diff and final plan statement.

**Calibration procedure (see §7 of the protocol for details):**

1. Run N=50 agent rollouts on held-out SWE-bench Lite tasks (not in Verified).
2. For each rollout, record Haiku's raw confidence score and ground-truth pass/fail.
3. Fit temperature T via scipy.optimize.minimize minimizing negative log-likelihood:
   ```
   p_calibrated = sigmoid(logit(raw) / T)
   ```
4. Select decision threshold τ* that minimizes expected cost at the equal-cost point
   (false-reject = false-accept). Under that cost structure, τ* = 0.5 after temperature
   scaling by construction. Document deviation if cost asymmetry is later discovered.

**Expected calibration output (pilot):**
- Pre-calibration Brier score: ~0.18 (high — Haiku over-confident on difficult tasks)
- Post-calibration Brier score: ~0.12 (target: < 0.15)
- Reliability diagram: deciles of predicted confidence should match observed frequency
  within ±0.05.

**Cost per verifier call (estimated):** ~$0.02-0.05. Well below 1% of per-task budget.

## V2: Strong Uncalibrated (Claude Opus 4.7 judge, default)

**Judge model:** Claude Opus 4.7. Same model family as the agent.

**Prompt:** identical to V1 (same text, different judge model). This is critical:
we want to vary *who the judge is*, not *what they're asked*.

**Calibration:** **none**. The judge outputs a raw confidence; we threshold at 0.5.
No temperature scaling. This is the scientific stand-in for "add a judge, move on"
as practiced in many research agents (Reflexion-inspired systems, many internal
agent papers).

**Expected behavior:**
- Brier score: likely worse than V1 despite stronger model, due to over-confidence.
  Strong models often produce 0.8-0.95 confidence on questions where their accuracy
  is 0.6-0.7 (see Kadavath et al. 2022 on self-knowledge; and Zhang et al. 2023 on
  LLM calibration).
- Rejection rate: sensitive to prompt's "strictness" instruction. Pre-registered
  prompt phrasing controls this.

**Cost per verifier call (estimated):** ~$0.15-0.30. Non-trivial fraction of
per-task budget (~5%).

## V3: Strong Calibrated (Claude Opus 4.7 judge, temperature-scaled)

**Judge model:** Claude Opus 4.7. Same prompt as V2.

**Calibration:** same temperature-scaling procedure as V1, run on Opus outputs
from the same 50-task calibration set.

**Expected behavior:**
- Brier score: the lowest of any variant if calibration is well-fit.
- Rejection rate: should be close to ground-truth failure rate on the held-out set
  (i.e., if 40% of rollouts actually fail, V3 should reject ~40% of the time).

**Cost per verifier call:** same as V2, ~$0.15-0.30.

## Calibration Diagnostics (pre-experiment acceptance criteria)

Before the main experiment runs, each calibrated variant must pass:

1. **Brier score** on held-out calibration set (50 tasks): < 0.15.
2. **Reliability diagram**: per-decile predicted vs observed accuracy differs by < 0.10
   in ≥ 8 of 10 deciles.
3. **Discrimination (AUC)**: > 0.65 (otherwise the verifier has no signal, calibrated
   or not).

If acceptance criteria fail on V1 (weak-calibrated), retry with 150-task calibration
set. If criteria still fail, report as a scientific finding — "Haiku cannot be
usefully calibrated on this task" — and drop V1 from the confirmatory analysis.

## Prompt Sensitivity Robustness Check

To confirm findings are not an artifact of prompt wording, we pre-register 3
paraphrases of the verifier prompt:

- **P1 (neutral, registered above).**
- **P2 (explicit):** "You are a senior engineer reviewing a junior's PR..."
- **P3 (impartial):** "Evaluate objectively using only the provided artifacts..."

Run P2, P3 on a 50-task subset for each variant. Report pass@1 agreement across
prompts (target: κ > 0.7). If agreement is poor, flag prompt sensitivity as a
primary finding of the paper.

## Verifier Audit

For each failed-and-verifier-rejected trajectory, a held-out human (or third
model, e.g., GPT-5) audits 10% of cases to confirm the verifier's reasoning is
grounded in the trajectory (not hallucinated). This is the "rubber-stamp
verification" check from the failure taxonomy: if the verifier is pattern-matching
on superficial features rather than reading the trajectory, calibration alone
won't fix it.

Audit criterion: verifier reasoning cites at least one specific step (tool call
or test result) from the trajectory in > 80% of sampled cases.

## Caveats and Non-Goals

**Not tested in this experiment:**
- Verifier-as-critic (generating feedback for retries). This experiment tests
  verifier-as-gate only.
- Multi-vote verifiers (ensembles). Single-shot verification is the base case.
- Tool-using verifiers (verifier can re-run tests). We test black-box judges only.

These are natural follow-ups; documented in the protocol §12 Expected Contributions.
