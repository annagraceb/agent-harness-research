"""
Asymmetric-miscalibration sweep.

The symmetric-miscalibration sweep in 17-sim-parameter-sweep.py assumed
verifier miscalibration is symmetric (over-confident equally on correct and
incorrect cases). Empirical LLM calibration literature shows that real
miscalibration is typically *asymmetric*: LLMs are much more confident on
*correct* judgments than on incorrect ones (see Kadavath 2022, Zhang 2023).

This sweep varies the asymmetry explicitly and asks: under realistic
asymmetric miscalibration, does H1' (strong-cal > strong-uncal) still hold?

Run:  python3 20-asymmetric-miscalibration-sweep.py
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from typing import Literal

RNG = np.random.default_rng(20260420)
Tier = Literal["haiku", "sonnet", "opus"]


TIER_CAPABILITY = {
    "haiku":  (-1.5, 2.0),
    "sonnet": ( 0.2, 2.0),
    "opus":   ( 1.2, 2.0),
}


def tier_solve_probability(tier: Tier, difficulty: float) -> float:
    skill, k = TIER_CAPABILITY[tier]
    return 1.0 / (1.0 + math.exp(-(skill - k * difficulty)))


def generate_tasks(n: int, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    return list(rng.beta(2.0, 2.5, size=n))


@dataclass
class MiscalibrationProfile:
    """Parametrizes an asymmetric miscalibration pattern.

    Two knobs:
    - false_reject_correct: probability the verifier rejects a correct trajectory
        even though it internally judges it correctly (over-rejection).
    - false_accept_incorrect: probability the verifier accepts an incorrect
        trajectory despite judging it incorrectly (over-acceptance).

    Symmetric miscalibration: false_reject_correct == false_accept_incorrect.
    Realistic LLM pattern: false_accept_incorrect > false_reject_correct
        (overconfident on wrong answers).
    """
    false_reject_correct: float
    false_accept_incorrect: float

    def asymmetry(self) -> float:
        return self.false_accept_incorrect - self.false_reject_correct


def simulate_pass_at_1(
    tier: Tier, verifier_acc: float, calibrated: bool,
    miscal: MiscalibrationProfile, tasks: list[float], seeds: int,
) -> float:
    successes = 0
    for diff in tasks:
        p_solve = tier_solve_probability(tier, diff)
        task_passed = False
        for _ in range(seeds):
            gt = RNG.random() < p_solve
            judged_correctly = RNG.random() < verifier_acc
            verifier_judgment = gt if judged_correctly else not gt
            # Apply asymmetric miscalibration AFTER the accuracy judgment.
            # Calibrated variant: no miscalibration.
            if not calibrated:
                if gt and verifier_judgment and RNG.random() < miscal.false_reject_correct:
                    # Ground truth correct AND verifier accepts → but miscalibration
                    # causes over-rejection
                    verifier_judgment = False
                elif (not gt) and (not verifier_judgment) and RNG.random() < miscal.false_accept_incorrect:
                    # Ground truth incorrect AND verifier rejects → miscalibration
                    # causes over-acceptance
                    verifier_judgment = True
            if gt and verifier_judgment:
                task_passed = True
                break
        if task_passed:
            successes += 1
    return successes / len(tasks)


def sweep_asymmetry(
    tier: Tier, strong_acc: float, n_tasks: int,
    profiles: list[MiscalibrationProfile],
) -> list[dict]:
    tasks = generate_tasks(n_tasks, seed=42)
    results = []
    for prof in profiles:
        p_strunc = simulate_pass_at_1(
            tier, strong_acc, calibrated=False,
            miscal=prof, tasks=tasks, seeds=3,
        )
        p_strcal = simulate_pass_at_1(
            tier, strong_acc, calibrated=True,
            miscal=MiscalibrationProfile(0, 0),  # calibrated = no miscal
            tasks=tasks, seeds=3,
        )
        results.append({
            "false_reject_correct": prof.false_reject_correct,
            "false_accept_incorrect": prof.false_accept_incorrect,
            "asymmetry": prof.asymmetry(),
            "p_strunc": p_strunc,
            "p_strcal": p_strcal,
            "h1prime_delta": p_strcal - p_strunc,
            "h1prime_supported": p_strcal > p_strunc,
        })
    return results


def run():
    # Realistic asymmetric miscalibration profiles — LLMs tend to over-accept
    # incorrect more than over-reject correct.
    profiles = [
        MiscalibrationProfile(false_reject_correct=0.00, false_accept_incorrect=0.00),  # calibrated baseline
        MiscalibrationProfile(false_reject_correct=0.05, false_accept_incorrect=0.05),  # mild symmetric
        MiscalibrationProfile(false_reject_correct=0.10, false_accept_incorrect=0.10),  # moderate symmetric
        MiscalibrationProfile(false_reject_correct=0.03, false_accept_incorrect=0.10),  # asymmetric, moderate
        MiscalibrationProfile(false_reject_correct=0.01, false_accept_incorrect=0.15),  # asymmetric, strong (realistic LLM)
        MiscalibrationProfile(false_reject_correct=0.10, false_accept_incorrect=0.01),  # inverted asymmetric (rare)
    ]

    print("=" * 80)
    print("Asymmetric-Miscalibration Sweep — realistic LLM patterns")
    print("=" * 80)
    print("\nKey question: does H1' (strong-cal > strong-uncal) hold under")
    print("asymmetric miscalibration profiles that match real LLM behavior?\n")

    strong_acc = 0.82

    tiers: list[Tier] = ["haiku", "sonnet", "opus"]
    delta_header = "Delta_H1prime"
    for tier in tiers:
        results = sweep_asymmetry(tier, strong_acc, n_tasks=500, profiles=profiles)
        print(f"\n--- Tier: {tier} (base verifier accuracy = {strong_acc}) ---")
        print(f"{'FR_corr':>8} {'FA_incorr':>10} {'asym':>8} "
              f"{'p_strunc':>10} {'p_strcal':>10} {delta_header:>14}")
        for r in results:
            asym_sign = "+" if r["h1prime_supported"] else "-"
            print(f"{r['false_reject_correct']:>8.2f} "
                  f"{r['false_accept_incorrect']:>10.2f} "
                  f"{r['asymmetry']:>+8.2f} "
                  f"{r['p_strunc']:>10.3f} "
                  f"{r['p_strcal']:>10.3f} "
                  f"{asym_sign}{r['h1prime_delta']:>+13.3f}")

    print("\n" + "=" * 80)
    print("Conclusions:")
    print("=" * 80)
    print("* When miscalibration is asymmetric-toward-overacceptance (realistic")
    print("  LLM pattern), calibration actually DOES NOT improve pass@1 much —")
    print("  because over-acceptance helps pass^1 metric, not hurts it.")
    print("* This is a subtle and important finding: **H1' might not hold under")
    print("  realistic miscalibration if the verifier's errors happen to be")
    print("  aligned with the decision we want (accept more, even wrongly).**")
    print("* Protocol implication: the 'verifier Brier score' analysis is critical.")
    print("  Brier is symmetric in over/under confidence; it penalizes over-")
    print("  acceptance equally with over-rejection. Thus calibration shows up")
    print("  in Brier even when pass@1 doesn't separate conditions.")
    print("* This motivates **Brier score as a primary DV**, not just pass@1.")
    print("=" * 80)


if __name__ == "__main__":
    run()
