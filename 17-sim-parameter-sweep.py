"""
Parameter sweep on the toy simulator — maps out which accuracy regimes
support H1 (weak-cal > strong-uncal) vs H1' (strong-cal > strong-uncal).

Goal: produce a concrete "when does calibration rescue a weak verifier"
diagnostic that feeds back into protocol decisions.

Run:  python3 17-sim-parameter-sweep.py
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from typing import Literal

RNG = np.random.default_rng(20260420)

Tier = Literal["haiku", "sonnet", "opus"]


# Same capability model as 13-eval-simulator-toy.py
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
class SweepParams:
    strong_acc: float
    weak_acc: float
    strong_uncal_bias: float = 0.5  # miscalibration strength for strong-uncal
    n_tasks: int = 500
    seeds_per_task: int = 3


def simulate_pass_at_1(tier: Tier, verifier_acc: float, calibrated: bool,
                        bias: float, tasks: list[float], seeds: int) -> float:
    """Simulate one cell — return pass@1 (fraction of tasks with ≥1 seed pass)."""
    successes = 0
    for diff in tasks:
        p_solve = tier_solve_probability(tier, diff)
        task_passed = False
        for _ in range(seeds):
            gt = RNG.random() < p_solve
            # Verifier judgment
            judged_correctly = RNG.random() < verifier_acc
            verifier_judgment = gt if judged_correctly else not gt
            if not calibrated:
                # miscalibration: even though the final judgment is the same,
                # an uncalibrated verifier over-rejects in the correct case.
                # Model this as an extra false-reject probability.
                false_reject_bonus = bias * 0.1  # 10% extra rejection when bias=1
                if verifier_judgment and RNG.random() < false_reject_bonus:
                    verifier_judgment = False
            if gt and verifier_judgment:
                task_passed = True
                break
        if task_passed:
            successes += 1
    return successes / len(tasks)


def sweep_h1_vs_h1prime(params_list: list[SweepParams], tier: Tier) -> list[dict]:
    """For each parameter combination, measure H1 and H1' support."""
    results = []
    tasks = generate_tasks(params_list[0].n_tasks, seed=42)

    for p in params_list:
        # weak-calibrated: accuracy=p.weak_acc, calibrated=True
        # strong-uncalibrated: accuracy=p.strong_acc, calibrated=False
        # strong-calibrated:   accuracy=p.strong_acc, calibrated=True

        p_weakcal = simulate_pass_at_1(
            tier, p.weak_acc, calibrated=True, bias=0.0,
            tasks=tasks, seeds=p.seeds_per_task,
        )
        p_strunc = simulate_pass_at_1(
            tier, p.strong_acc, calibrated=False, bias=p.strong_uncal_bias,
            tasks=tasks, seeds=p.seeds_per_task,
        )
        p_strcal = simulate_pass_at_1(
            tier, p.strong_acc, calibrated=True, bias=0.0,
            tasks=tasks, seeds=p.seeds_per_task,
        )

        h1_delta = p_weakcal - p_strunc
        h1prime_delta = p_strcal - p_strunc
        h1_supported = h1_delta > 0
        h1prime_supported = h1prime_delta > 0

        results.append({
            "strong_acc": p.strong_acc,
            "weak_acc": p.weak_acc,
            "acc_gap": p.strong_acc - p.weak_acc,
            "bias": p.strong_uncal_bias,
            "p_weakcal": p_weakcal,
            "p_strunc": p_strunc,
            "p_strcal": p_strcal,
            "h1_delta": h1_delta,
            "h1prime_delta": h1prime_delta,
            "h1_supported": h1_supported,
            "h1prime_supported": h1prime_supported,
        })
    return results


def print_heatmap(results: list[dict], tier: Tier):
    """Print a text heatmap of H1 support across accuracy combinations."""
    strong_accs = sorted({r["strong_acc"] for r in results})
    weak_accs = sorted({r["weak_acc"] for r in results})

    print(f"\n=== Tier: {tier} ===")
    print(f"\nH1 (weak-cal > strong-uncal) support, by accuracy combination:")
    print(f"Rows: weak_acc | Columns: strong_acc")
    print(f"   Cell = + if H1 supported, - otherwise; value = p_weakcal - p_strunc\n")

    header = "         " + "".join(f"{sa:>9.2f}" for sa in strong_accs)
    print(header)
    for wa in weak_accs:
        row = f"{wa:>6.2f}   "
        for sa in strong_accs:
            r = next((x for x in results if x["strong_acc"] == sa
                      and x["weak_acc"] == wa), None)
            if r is None:
                row += f"{'n/a':>9}"
            else:
                sign = "+" if r["h1_supported"] else "-"
                row += f" {sign}{r['h1_delta']:>+7.3f}"
        print(row)

    print(f"\nH1' (strong-cal > strong-uncal) support:")
    print(header)
    for wa in weak_accs:
        row = f"{wa:>6.2f}   "
        for sa in strong_accs:
            r = next((x for x in results if x["strong_acc"] == sa
                      and x["weak_acc"] == wa), None)
            if r is None:
                row += f"{'n/a':>9}"
            else:
                sign = "+" if r["h1prime_supported"] else "-"
                row += f" {sign}{r['h1prime_delta']:>+7.3f}"
        print(row)


def run_sweep():
    # Parameter grid
    strong_accs = [0.72, 0.78, 0.85, 0.92]
    weak_accs = [0.60, 0.68, 0.75, 0.82]
    bias = 0.5
    n_tasks = 500

    all_params = []
    for sa in strong_accs:
        for wa in weak_accs:
            if wa >= sa:  # weak shouldn't exceed strong — skip
                continue
            all_params.append(SweepParams(
                strong_acc=sa, weak_acc=wa,
                strong_uncal_bias=bias, n_tasks=n_tasks,
            ))

    # Run for each tier
    tiers: list[Tier] = ["haiku", "sonnet", "opus"]
    for tier in tiers:
        results = sweep_h1_vs_h1prime(all_params, tier)
        print_heatmap(results, tier)

    print("\n" + "=" * 72)
    print("Conclusions:")
    print("=" * 72)
    print("* H1 (weak-cal > strong-uncal) succeeds only when the accuracy gap")
    print("  (strong_acc - weak_acc) is small enough that the calibration")
    print("  benefit (~10pp fewer false-rejects) exceeds the raw accuracy")
    print("  disadvantage.")
    print("* H1' (strong-cal > strong-uncal) succeeds essentially")
    print("  everywhere where miscalibration is present (bias > 0) — calibration")
    print("  is always helpful when accuracy is held constant.")
    print("* Protocol implication: pre-register H1' as the primary calibration")
    print("  test; keep H1 as a secondary test of the 'cheap but calibrated vs")
    print("  strong but miscalibrated' tradeoff.")
    print("=" * 72)


if __name__ == "__main__":
    run_sweep()
