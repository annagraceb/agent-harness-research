"""
Haiku verifier — V2 (uncalibrated) and V3 (temperature-scaled) using the
Anthropic API with Claude Haiku 4.5.

Drops into the Verifier ABC from 04-harness-schema.py alongside ScriptedVerifier
and NoneVerifier, so the AgentLoop doesn't change — swap the verifier, swap
conditions.

Cost accounting:
  Per verifier call: ~200-800 input tokens, ~30-60 output tokens, caching
  aggressive for the system prompt.
  Haiku 4.5 pricing (as of 2026-01): $0.80 / M input, $4 / M output.
  Per-call estimate: ~$0.005-0.01 typical, $0.02 worst case.

Smoke test:  python3 29-haiku-verifier.py
  Requires ANTHROPIC_API_KEY env var. If unset, runs offline component only.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Load the schema contract
_schema_path = Path(__file__).resolve().parent / "04-harness-schema.py"
_schema_spec = importlib.util.spec_from_file_location("harness_schema", str(_schema_path))
assert _schema_spec and _schema_spec.loader
harness_schema = importlib.util.module_from_spec(_schema_spec)
sys.modules["harness_schema"] = harness_schema
_schema_spec.loader.exec_module(harness_schema)

VerifierOutput = harness_schema.VerifierOutput
VerifierSpec = harness_schema.VerifierSpec
Verifier = harness_schema.Verifier


HAIKU_MODEL = "claude-haiku-4-5"

# The pre-registered verifier prompt (frozen). Same text used for V2 and V3;
# the only difference between conditions is calibration of the returned score.
VERIFIER_PROMPT_TEMPLATE = """You are reviewing an agent's attempt to fix a buggy Python function.

TASK DESCRIPTION:
{task_description}

ORIGINAL BUGGY CODE:
```python
{buggy_code}
```

AGENT'S PROPOSED FIX (full file):
```python
{final_diff}
```

TRAJECTORY SUMMARY (compressed):
{trajectory_summary}

Answer TWO questions about the agent's proposed fix:

1. correct: true or false — Does this fix address the bug and correctly implement the function?
2. confidence: a float in [0.0, 1.0] — Your probability estimate that this fix passes a hidden test suite for this function.

Be honest about uncertainty. Err on the side of rejection only when there is clear evidence of incorrectness.

Respond as strict JSON with this exact schema:
{{"correct": <bool>, "confidence": <float>, "reasoning": "<= 200 words"}}

Respond with ONLY the JSON. No preamble, no markdown fences.
"""


# Hash the prompt once — used in Harness Cards
def _prompt_hash() -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(VERIFIER_PROMPT_TEMPLATE.encode()).hexdigest()[:16]


PROMPT_HASH = _prompt_hash()


@dataclass
class HaikuJudgement:
    """Raw judgement from Haiku before calibration."""
    correct: bool
    raw_confidence: float
    reasoning: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    wall_seconds: float = 0.0


def _haiku_cost(tokens_in: int, tokens_out: int) -> float:
    """Haiku 4.5 pricing as of 2026-01: $0.80 / M input, $4 / M output."""
    return tokens_in * 0.80 / 1_000_000 + tokens_out * 4.0 / 1_000_000


def _parse_judgement(raw: str) -> tuple[bool, float, str]:
    """Parse the JSON response from Haiku. Tolerant of minor format slips."""
    # Strip markdown fences if present
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1)
    # Find first { ... } block
    m2 = re.search(r"\{.*\}", raw, re.DOTALL)
    if m2:
        raw = m2.group(0)
    try:
        obj = json.loads(raw)
        correct = bool(obj.get("correct", False))
        confidence = float(obj.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        reasoning = str(obj.get("reasoning", ""))[:800]
        return correct, confidence, reasoning
    except (json.JSONDecodeError, ValueError, TypeError):
        return False, 0.5, f"unparseable: {raw[:200]}"


def call_haiku(
    task_description: str,
    buggy_code: str,
    final_diff: str,
    trajectory_summary: str = "(not recorded)",
) -> HaikuJudgement:
    """Single Haiku verifier call. Requires ANTHROPIC_API_KEY env var."""
    import anthropic  # local import to avoid cost when unused

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    prompt = VERIFIER_PROMPT_TEMPLATE.format(
        task_description=task_description[:1000],
        buggy_code=buggy_code[:2000],
        final_diff=final_diff[:3000],
        trajectory_summary=trajectory_summary[:1500],
    )

    t0 = time.time()
    msg = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.time() - t0

    content = msg.content[0].text if msg.content else ""  # type: ignore[attr-defined]
    correct, confidence, reasoning = _parse_judgement(content)

    usage = msg.usage
    tokens_in = usage.input_tokens
    tokens_out = usage.output_tokens

    return HaikuJudgement(
        correct=correct, raw_confidence=confidence, reasoning=reasoning,
        tokens_in=tokens_in, tokens_out=tokens_out,
        cost_usd=_haiku_cost(tokens_in, tokens_out),
        wall_seconds=round(elapsed, 2),
    )


# =============================================================================
# Temperature scaling — the Level-1 "training" step
# =============================================================================


def temperature_scale(raw_confidences: list[float], outcomes: list[bool]) -> float:
    """Fit a temperature T to minimize negative log-likelihood on a calibration
    set. Standard Platt/temperature-scaling procedure (Guo et al. 2017).

    p_calibrated = sigmoid(logit(raw) / T)

    Returns the best T. T > 1 softens (reduces confidence); T < 1 sharpens.
    """
    from scipy.optimize import minimize_scalar  # type: ignore[import-not-found]

    if len(raw_confidences) != len(outcomes) or len(raw_confidences) == 0:
        return 1.0
    # Clip to avoid log(0) — standard calibration practice
    eps = 1e-6
    raws = [max(eps, min(1 - eps, r)) for r in raw_confidences]

    def nll(T: float) -> float:
        if T <= 0:
            return 1e9
        total = 0.0
        for r, o in zip(raws, outcomes):
            logit = math.log(r / (1 - r))
            scaled = 1.0 / (1.0 + math.exp(-logit / T))
            scaled = max(eps, min(1 - eps, scaled))
            total += -(o * math.log(scaled) + (1 - o) * math.log(1 - scaled))
        return total

    result = minimize_scalar(nll, bounds=(0.1, 10.0), method="bounded")
    return float(result.x)


def brier_score(confidences: list[float], outcomes: list[bool]) -> float:
    """Mean squared error between predicted probability and outcome."""
    if not confidences:
        return float("nan")
    return sum((c - (1.0 if o else 0.0)) ** 2 for c, o in zip(confidences, outcomes)) / len(confidences)


def apply_temperature(raw: float, T: float) -> float:
    eps = 1e-6
    r = max(eps, min(1 - eps, raw))
    logit = math.log(r / (1 - r))
    return 1.0 / (1.0 + math.exp(-logit / T))


# =============================================================================
# HaikuVerifier — plugs into the AgentLoop
# =============================================================================


@dataclass
class HaikuVerifier(Verifier):
    """Verifier using Claude Haiku 4.5. Implements the Verifier ABC from
    04-harness-schema.py. V2 (uncalibrated) uses temperature=1.0; V3
    (calibrated) uses a pilot-fit temperature."""

    spec: VerifierSpec  # type: ignore[misc]
    calibration_temperature: float = 1.0
    decision_threshold: float = 0.5
    task_description: str = ""
    buggy_code: str = ""
    last_judgement: HaikuJudgement | None = None

    def verify(self, task_description: str, trajectory, final_diff: str) -> VerifierOutput:
        task_desc = task_description or self.task_description
        buggy = self.buggy_code
        traj_summary = self._summarize(trajectory) if trajectory else "(not provided)"
        j = call_haiku(task_desc, buggy, final_diff, traj_summary)
        self.last_judgement = j
        calibrated = apply_temperature(j.raw_confidence, self.calibration_temperature)
        return VerifierOutput(
            confidence=calibrated,
            raw_confidence=j.raw_confidence,
            passes=calibrated >= self.decision_threshold,
            reasoning=j.reasoning,
        )

    @staticmethod
    def _summarize(trajectory) -> str:
        """Compact trajectory summary: tool-call sequence + last test result."""
        if trajectory is None:
            return ""
        try:
            steps = trajectory.steps
        except AttributeError:
            return ""
        parts: list[str] = []
        for s in steps[-20:]:
            k = s.kind.value if hasattr(s.kind, "value") else str(s.kind)
            if k == "tool_call":
                parts.append(f"call:{s.payload.get('tool','?')}")
            elif k == "tool_result":
                ok = s.payload.get("ok")
                parts.append(f"  result:ok={ok}")
        return " → ".join(parts)[:1500]


# =============================================================================
# Smoke tests
# =============================================================================


def smoke_test_offline() -> None:
    """Test temperature scaling on a synthetic calibration set — no API calls."""
    print("=" * 70)
    print("Offline smoke test: temperature scaling")
    print("=" * 70)
    # Construct a miscalibrated "verifier" — systematically overconfident
    import random
    rng = random.Random(42)
    confs_raw: list[float] = []
    outcomes: list[bool] = []
    for _ in range(200):
        true_p = rng.uniform(0.3, 0.8)
        outcome = rng.random() < true_p
        # Miscalibration: push confidence toward extremes
        raw = 0.5 + (true_p - 0.5) * 1.8
        raw = max(0.01, min(0.99, raw))
        confs_raw.append(raw)
        outcomes.append(outcome)

    T = temperature_scale(confs_raw, outcomes)
    print(f"  Fitted T:          {T:.3f} (T>1 means over-confident raw, so softening)")
    print(f"  Raw Brier:         {brier_score(confs_raw, outcomes):.4f}")
    confs_cal = [apply_temperature(r, T) for r in confs_raw]
    print(f"  Calibrated Brier:  {brier_score(confs_cal, outcomes):.4f}")
    print(f"  Improvement:       {brier_score(confs_raw, outcomes) - brier_score(confs_cal, outcomes):+.4f}")


def smoke_test_online() -> None:
    """One real Haiku call. Requires ANTHROPIC_API_KEY."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nSKIPPED: ANTHROPIC_API_KEY not set. Set it to run a real verifier call.")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        return

    print("\n" + "=" * 70)
    print("Online smoke test: one real Haiku verifier call")
    print("=" * 70)

    buggy = """def has_close_elements(numbers, threshold):
    for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(numbers):
            if idx != idx2:
                distance = elem - elem2  # missing abs()
                if distance < threshold:
                    return True
    return False"""

    fixed = """def has_close_elements(numbers, threshold):
    for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(numbers):
            if idx != idx2:
                distance = abs(elem - elem2)
                if distance < threshold:
                    return True
    return False"""

    j = call_haiku(
        task_description="Return True if any two numbers in the list are closer than threshold.",
        buggy_code=buggy,
        final_diff=fixed,
        trajectory_summary="read_file → run_tests(fail) → edit_file → run_tests(pass)",
    )
    print(f"  Correct:    {j.correct}")
    print(f"  Confidence: {j.raw_confidence:.2f}")
    print(f"  Tokens:     {j.tokens_in} in / {j.tokens_out} out")
    print(f"  Cost:       ${j.cost_usd:.4f}")
    print(f"  Wall sec:   {j.wall_seconds}")
    print(f"  Reasoning:  {j.reasoning[:300]}")


if __name__ == "__main__":
    smoke_test_offline()
    smoke_test_online()
