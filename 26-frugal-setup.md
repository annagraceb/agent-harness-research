# Frugal Experiment — Setup and Plan

*Concrete path from "I have an RTX 3060 and $50 of Anthropic credits" to
real data on the verifier-calibration hypothesis. No more spec — this is the
execution plan.*

---

## Verified environment (2026-04-20)

| Component | Status |
|-----------|--------|
| GPU | NVIDIA RTX 3060, 12 GB VRAM ✓ |
| CUDA | Available (torch 2.5.1+cu121, `cuda.is_available() = True`) ✓ |
| Ollama | v0.5.5 installed, daemon reachable at localhost:11434 ✓ |
| Python stack | `torch`, `transformers 4.57.6`, `datasets 4.8.4`, `numpy`, `pandas`, `matplotlib`, `pydantic 2.9.1` ✓ |
| Local models pulled | `deepseek-r1:latest` (4.7 GB), `llama2:latest` (3.8 GB), `qwen2.5-coder:7b` (pulling) |

## The plan in one paragraph

Use **Qwen-2.5-Coder-7B** (pulling now) as the base agent; use **DeepSeek-R1**
as the V1 local-judge verifier; use **Claude Haiku 4.5** (API) as V2/V3
verifier. Run on **HumanEvalFix** (164 tasks, public, right difficulty for a
7B coder). Target ~50 tasks × 3 seeds × 4 conditions = 600 agent rollouts
+ ~300 API verifier calls. Total estimated cost: **~$15-25 of the $50 budget**,
**~50 hours of 3060 time**.

Publishable output: a proof-of-concept paper showing the verifier-calibration
protocol from `02-verifier-calibration-protocol.md` actually works on real
data at a $25 budget, with `H1'a` (Brier-based validity) answered
definitively and `H1'b` (pass@1 transfer) reported directionally.

## What's built so far

| Artifact | Status |
|----------|--------|
| `04-harness-schema.py` — AgentLoop + Harness Card v1.0 + LLMClient Protocol | ✓ (smoke-tested) |
| `27-ollama-adapter.py` — bridges a local Ollama model to the LLMClient Protocol | ✓ (smoke-tested with DeepSeek-R1) |
| HumanEvalFix task loader | pending |
| Per-task agent-loop runner | pending (next) |
| Haiku verifier bridge | pending (V2 / V3) |
| Calibration fitter (temperature scaling) | pending |

## Next concrete steps, ordered

### Step 1: Finish the Qwen-2.5-Coder pull (in progress)
~4-5 GB download. Running in background. Verify with `ollama list` when done.

### Step 2: Build the HumanEvalFix loader
Use HuggingFace `datasets` to pull `bigcode/humanevalpack` (the
HumanEvalFix subset). Wrap each task in a `Task` object per
`04-harness-schema.py`.

Stub task:

```python
from datasets import load_dataset
ds = load_dataset("bigcode/humanevalpack", "python", split="test")
# Each row has: prompt, buggy_solution, canonical_solution, test, ...
```

### Step 3: Build a real tool set

Replace `FakeSearchTool` / `FakeEditTool` in `04-harness-schema.py` with
tools that actually manipulate task files in a sandbox directory:

- `read_file(path)` — return file contents
- `edit_file(path, diff)` — apply a unified diff
- `run_tests()` — execute the task's test suite, return pass/fail + stderr

Sandbox each task in `/tmp/frugal-runs/task_N_seed_M/`. Agent sees only
its sandbox; ground-truth tests run there too.

### Step 4: Wire up two verifiers

**V1 (local judge):** a second `OllamaLLM` instance with DeepSeek-R1 as
model. Same Protocol contract.

**V2 / V3 (Haiku API):** small wrapper calling Anthropic's
`claude-haiku-4-5` via their Python SDK. V3 applies temperature-scaled
confidence from a calibration fit.

### Step 5: Pilot run (20 tasks × 1 seed × 2 conditions)

- Conditions: V0 (none) vs V3 (Haiku strong-calibrated)
- Target cost: <$2 of Anthropic credits, ~4 hours of 3060 time
- Goals: confirm the full pipeline works end-to-end; produce real pass@1
  numbers; measure agent-loop wall-clock per task

### Step 6: Calibration fit

Run V2 (Haiku uncalibrated) on the same 20 pilot tasks. Fit temperature T
via `scipy.optimize.minimize` on NLL of Haiku's confidences vs. ground
truth. Freeze T for V3.

### Step 7: Main run (50 tasks × 3 seeds × 4 conditions)

- Conditions: V0, V1 (local judge), V2, V3
- Target cost: ~$15 (V2 + V3 API calls on 50 × 3 × 2 = 300 verifier calls)
- Target wall-clock: ~40-50 hours on the 3060
- Can be batched: run subsets overnight, resume

### Step 8: Analysis

Apply the pre-registered tests from `06-statistical-analysis-plan.md`:
- H1'a (Brier): `Brier(V3) < Brier(V2)` via bootstrap CI
- H1'b (pass@1): `pass@1(V3) > pass@1(V2)` via two-proportion z-test

Because N=50 and single-tier, don't over-claim. Report as proof-of-concept
with 95% CIs, not as confirmatory evidence for the full scaffolding-shadow
hypothesis.

## What "training" can mean here

Three different levels:

### Level 0 — No training, pure inference
Steps 1-8 above. This is the minimum-viable frugal experiment.

### Level 1 — Temperature-scaling calibration (trivial training)
Step 6 above. **One scalar parameter fit on ~50 trajectories.** Takes
seconds of compute. Technically "training" — it's MLE optimization — but
barely.

### Level 2 — LoRA-adapted local verifier (real training)
*Optional extension:* fine-tune the DeepSeek-R1 verifier with QLoRA on
pairs of (diff, ground-truth-pass) from HumanEvalPack's train split.
Makes the local judge a *specialized* verifier, not just a zero-shot
reasoning model. Fits in ~10 GB VRAM with 4-bit quantization.
Publishable as "frugal verifier distillation."

| Training target | VRAM need | Time on 3060 | Scientific value |
|-----------------|----------:|-------------:|------------------|
| Temperature scaling (Level 1) | <1 GB | seconds | required for H1'a validity |
| LoRA on 1-3B model (Level 2-lite) | ~6 GB | ~4 hours | bonus; tests "distilled verifier" hypothesis |
| LoRA on 7B model (Level 2) | ~10 GB | ~12-24 hours | the real training run |

**Recommendation: start with Level 0/1, then do Level 2-lite if time
permits.** Level 2 full is ambitious for a solo-researcher timeline but
not impossible — it's a weekend project.

## What it costs to get started right now

Nothing. Steps 1-2 are entirely free (model download + dataset download
from HuggingFace). Steps 3-5 require no API credits (pilot is V0 vs V3;
V0 is free, V3 costs ~$1-2 for 20 tasks).

The Anthropic $50 is reserved for Steps 5+7 — the pilot verifier calls
and the main 300-call verifier run.

## Stopping criteria

- **Green flag (full run):** pilot achieves pass@1 > 15% on V0 condition
  (sanity check that the agent actually solves some tasks). Full run goes.
- **Yellow flag (scope down):** pilot pass@1 is 5-15%. Switch to easier
  benchmark (HumanEval instead of HumanEvalFix) or stronger agent model.
- **Red flag (pivot):** pilot pass@1 < 5%. Agent can't solve HumanEvalFix
  reliably; calibration data is too sparse. Pivot to Level 0 "retrospective
  verifier on Princeton trajectories" plan — use public SWE-agent logs
  as the source of agent behavior, add only the verifier layer.

## Today's concrete deliverable (T19)

- `27-ollama-adapter.py` — built and smoke-tested ✓
- `26-frugal-setup.md` — this document ✓
- Qwen-2.5-Coder-7B pulled — in progress, background

Next session: Step 2 (HumanEvalFix loader) and Step 3 (real tool set).
Aim for end-to-end single-task run on real data.

---

## Appendix A — Commands you can run right now

```bash
# Check what Ollama has locally
ollama list

# Pull Qwen-2.5-Coder 7B (if not already done)
ollama pull qwen2.5-coder:7b

# Smoke-test the adapter
python3 27-ollama-adapter.py

# Pull HumanEvalFix
python3 -c "from datasets import load_dataset; \
           d = load_dataset('bigcode/humanevalpack', 'python', split='test'); \
           print(len(d), 'tasks;', d[0].keys())"

# Check adapter's request log
ls logs/ && tail -1 logs/ollama_smoke_*.jsonl
```
