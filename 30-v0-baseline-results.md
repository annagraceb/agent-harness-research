# V0 Baseline Results — First Real Data

*50-task pass-rate baseline for Qwen-2.5-Coder-7B on HumanEvalFix using our
harness (no verifier, V0 condition). Run 2026-04-20 on RTX 3060, local
inference via Ollama, $0 API cost.*

---

## Headline

**22 / 50 = 44.0% pass rate.** Wilson 95% CI: [31.2%, 57.7%].

Total wall clock: 15.3 minutes. Mean 18.3 s/task.
Total tokens: 407,748 in / 26,653 out. Cost: $0 (local inference).

## Why this is a useful baseline

- Establishes the **V0 (no verifier) floor** for the verifier-calibration
  protocol at the Qwen-Coder-7B tier.
- Wide confidence interval (26 points) reflects honest N=50 uncertainty;
  larger N tightens this but isn't needed to proceed.
- 28 fails give plenty of verifier-calibration signal — Brier-score
  computations need both pass and fail outcomes; a 44/56 split is near-ideal
  for calibration.

## Failure-mode breakdown

| Pattern | Count | Signature |
|---------|------:|-----------|
| Budget exhaustion (turns=15) | 20 | Agent stuck editing/running without convergence — tool_thrash or edit-loop |
| Early termination (turns<=8) | 8 | Agent emitted `<final>` before tests passed — a self-confidence miscalibration |

71% of failures are budget-exhaustion. This suggests that **raising the turn
budget** (even modestly, 15 → 25) might catch several more, but at the cost
of more wall time per failure. A verifier intervention that **terminates
dead-end trajectories early** (forfeit bad paths) would also help — which is
exactly one of the mechanisms V3 (strong-calibrated verifier) is designed to
enable.

## Task-level pass pattern

- Tasks 0-9: **9 / 10 = 90%** (easy warm-up)
- Tasks 10-49: **13 / 40 ≈ 32%** (harder tail)

**Important lesson:** the first 10 tasks were *not* representative.
HumanEvalFix gets substantially harder after the first block. Running only
10 tasks gave a badly-optimistic 90% estimate; the full 50-task run
corrects to 44%. This mirrors the "task-distribution imbalance" confounder
documented in `02-verifier-calibration-protocol.md` §8.

This is itself a methodology finding worth recording: **N=10 on HumanEvalFix
is not enough to estimate baseline pass rate at the Qwen-Coder-7B tier.**
Anyone planning to run a similar frugal experiment should use N ≥ 30 for
first-pass estimates.

## Token budget implications

At 8,155 in / 533 out per task average:

| Verifier call | Input | Output | Cost (Haiku 4.5) |
|---------------|------:|-------:|-----------------:|
| Per task × 1 seed × 1 verifier cond | ~500 | ~100 | ~$0.001 |
| 50 tasks × 3 seeds × 2 verifier conds (V2+V3) | 150k | 30k | **~$0.24** |

The $50 Anthropic budget is essentially unspent after a full verifier run.
We have enormous headroom for calibration expansion, prompt paraphrase
robustness checks, and cross-model comparisons.

## Prompt sensitivity caveat

Earlier in the session, a minimal system prompt gave **1/5 = 20%** on a
5-task subset. The improved prompt (explicit protocol, few-shot example)
moved a 10-task subset to 90%. Full 50-task with improved prompt: 44%.

**Implication:** the first 20% result was probably a prompt-compliance
failure (agent didn't know how to use the tagged format). Once format
compliance is solved, the ceiling appears to be ~44% at this model scale —
consistent with published single-turn Qwen-Coder-7B HumanEvalFix numbers
(~50%). Harness overhead at the improved-prompt level is thus small (~6pp)
at this scale.

This is a data point *against* a naive version of the scaffolding-shadow
hypothesis at Qwen-7B scale: at this capability level, good-enough
scaffolding + small model mostly recovers single-turn performance. We'd
need to see whether harness variation produces a LARGER spread at Sonnet /
Opus tiers — which is the scaffolding-shadow prediction.

## Next experimental steps

With V0 established at 44%, the frugal protocol plan is:

1. **Pilot (10-20 tasks, V2 Haiku-uncalibrated)** — collect raw Haiku
   confidences paired with ground-truth outcomes. Cost: ~$0.05-0.10.
2. **Fit temperature T** using `29-haiku-verifier.py::temperature_scale()`.
3. **Main run (all 50 tasks, V2 + V3, 3 seeds each)** — ~$0.25 total.
4. **Compute H1'a (Brier test) and H1'b (pass@1 transfer test).**

Total projected Anthropic spend: well under $1 of the $50 budget. We can
repeat across prompt paraphrases for robustness.

## Honest limitations

- **Single seed per task** (this baseline run). Multi-seed needed for
  pass^k reliability claims.
- **Single tier** (Qwen-Coder-7B only). Cannot test scaffolding-shadow
  cross-tier interaction at this scale — would need at least one more tier.
- **HumanEvalFix is not SWE-bench.** Results don't transfer directly to
  more realistic software-engineering benchmarks.
- **44% is not 50%.** Our harness is slightly costing the agent vs. the
  published single-turn baseline, though the gap is within normal
  evaluation variance.

## Data release

`logs/v0_baseline_50.jsonl` contains one row per task with: task_id, pass,
turns_used, wall_seconds, tokens_in, tokens_out. Released with this commit
for reproducibility. RNG seed pinned at 20260420 throughout.

To reproduce:

```bash
python3 -c "
import importlib.util, sys, shutil, json, time
from pathlib import Path
spec = importlib.util.spec_from_file_location('fr', '28-frugal-runtime.py')
fr = importlib.util.module_from_spec(spec); sys.modules['fr'] = fr
spec.loader.exec_module(fr)
tasks = fr.load_humanevalfix(limit=50)
# ... (see logs/v0_baseline_50.jsonl for reference output)
"
```
