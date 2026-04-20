"""
Budget-sensitivity simulation — given a budget B, what's the optimal
experiment configuration and what hypotheses become answerable?

Answers the user's question: can we do less than the $140k program and still
produce a real scientific result?

For each (budget, tier_mix) pair, computes:
  * Max affordable N per cell
  * Power on the three primary hypotheses (H1'a Brier, H1'b pass@1, H2 shadow)
  * Which hypotheses are answerable at what confidence

Run:  python3 24-budget-sensitivity-simulation.py
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass

RNG = np.random.default_rng(20260420)


# -----------------------------------------------------------------------------
# Cost model
# -----------------------------------------------------------------------------
# Per-rollout cost estimates (agent + verifier combined) per tier.
# Based on Claude 4.x API prices as of 2026-01 and average trajectory length
# on SWE-bench (~40k input, ~8k output per rollout).

COST_PER_ROLLOUT = {
    "haiku":  0.40,
    "sonnet": 1.50,
    "opus":   4.00,
}

# Prior pass@1 from 02-protocol / 03-power-analysis
PRIOR_PASS_AT_1 = {
    "haiku":  {"none": 0.10, "weak-cal": 0.13, "strong-uncal": 0.11, "strong-cal": 0.15},
    "sonnet": {"none": 0.32, "weak-cal": 0.37, "strong-uncal": 0.30, "strong-cal": 0.40},
    "opus":   {"none": 0.52, "weak-cal": 0.57, "strong-uncal": 0.49, "strong-cal": 0.60},
}

CONDITIONS = ["none", "weak-cal", "strong-uncal", "strong-cal"]
SEEDS_PER_TASK = 3


# -----------------------------------------------------------------------------
# Budget → N calculation
# -----------------------------------------------------------------------------


@dataclass
class ExperimentConfig:
    tier_mix: tuple[str, ...]
    n_per_cell: int
    total_cost: float

    @property
    def n_cells(self) -> int:
        return len(self.tier_mix) * len(CONDITIONS)

    @property
    def total_rollouts(self) -> int:
        return self.n_cells * self.n_per_cell * SEEDS_PER_TASK


def max_n_for_budget(budget: float, tier_mix: tuple[str, ...]) -> ExperimentConfig:
    """Given a budget and tier mix, return the max N per cell that fits."""
    # Per-cell cost for one tier = N tasks × 3 seeds × cost_per_rollout
    # Total = sum over tiers of (4 conditions × 3 × N × tier_cost)
    per_n_cost = sum(
        len(CONDITIONS) * SEEDS_PER_TASK * COST_PER_ROLLOUT[t]
        for t in tier_mix
    )
    n = int(budget / per_n_cost)
    # Cap at 2000 (no point sampling more tasks than the benchmark has + augmented)
    n = min(n, 2000)
    # Floor at 0
    n = max(n, 0)
    total_cost = n * per_n_cost
    return ExperimentConfig(tier_mix=tier_mix, n_per_cell=n, total_cost=total_cost)


# -----------------------------------------------------------------------------
# Power calculation (Monte-Carlo, same methodology as 03-power-analysis.py)
# -----------------------------------------------------------------------------


def power_h1b_at_tier(tier: str, n: int, n_sims: int = 500) -> float:
    """H1'b: pass@1(strong-cal) > pass@1(strong-uncal) within tier."""
    if n < 30:
        return 0.0
    p1 = PRIOR_PASS_AT_1[tier]["strong-cal"]
    p2 = PRIOR_PASS_AT_1[tier]["strong-uncal"]
    rejections = 0
    for _ in range(n_sims):
        a = RNG.binomial(1, p1, size=n).mean()
        b = RNG.binomial(1, p2, size=n).mean()
        # One-sided test
        p_pool = (a + b) / 2
        se = math.sqrt(p_pool * (1 - p_pool) * 2 / n)
        if se == 0:
            continue
        z = (a - b) / se
        if z > 1.645:
            rejections += 1
    return rejections / n_sims


def power_h2_shadow(tier_mix: tuple[str, ...], n: int, n_sims: int = 500) -> float:
    """H2: R(opus) - R(haiku) > 0.03. Requires haiku AND opus in tier_mix."""
    if "haiku" not in tier_mix or "opus" not in tier_mix:
        return 0.0  # not testable
    if n < 30:
        return 0.0
    rejections = 0
    for _ in range(n_sims):
        # Simulate cell means for each tier
        ranges = {}
        for t in ("haiku", "opus"):
            cell_means = [
                RNG.binomial(1, PRIOR_PASS_AT_1[t][c], size=n).mean()
                for c in CONDITIONS
            ]
            ranges[t] = max(cell_means) - min(cell_means)
        if ranges["opus"] - ranges["haiku"] > 0.03:
            rejections += 1
    return rejections / n_sims


def power_h1a_brier(n: int) -> float:
    """H1'a: Brier(strong-cal) < Brier(strong-uncal).

    Under the calibration procedure (temperature scaling) this is near-deterministic
    if N > 100 — calibration minimizes Brier by construction on the calibration set
    and transfers to the test set with high probability.

    Approximation: power → 0.99 for any N ≥ 100; 0 below.
    """
    if n < 100:
        return 0.0
    return 0.99


# -----------------------------------------------------------------------------
# Main sweep
# -----------------------------------------------------------------------------


def sweep() -> list[dict]:
    budgets = [2_000, 5_000, 10_000, 15_000, 30_000, 50_000, 100_000, 140_000]
    tier_mixes: list[tuple[str, ...]] = [
        ("sonnet",),
        ("haiku", "sonnet"),
        ("sonnet", "opus"),
        ("haiku", "sonnet", "opus"),
    ]

    results = []
    for budget in budgets:
        for tier_mix in tier_mixes:
            cfg = max_n_for_budget(budget, tier_mix)
            if cfg.n_per_cell < 50:
                # Under-powered by construction; skip
                results.append({
                    "budget": budget, "tier_mix": "+".join(tier_mix),
                    "n_per_cell": cfg.n_per_cell, "total_cost": cfg.total_cost,
                    "total_rollouts": cfg.total_rollouts,
                    "power_h1a_brier": 0.0,
                    "power_h1b_pass1_best_tier": 0.0,
                    "power_h2_shadow": 0.0,
                    "answerable": "(too few tasks)",
                })
                continue

            # H1'a: Brier-based (works at any N ≥ 100)
            p_h1a = power_h1a_brier(cfg.n_per_cell)

            # H1'b: pass@1-based, best tier in the mix
            p_h1b_per_tier = {
                t: power_h1b_at_tier(t, cfg.n_per_cell) for t in tier_mix
            }
            p_h1b_best = max(p_h1b_per_tier.values())
            best_tier = max(p_h1b_per_tier, key=lambda t: p_h1b_per_tier[t])

            # H2: shadow, requires haiku + opus
            p_h2 = power_h2_shadow(tier_mix, cfg.n_per_cell)

            # Which hypotheses are answerable at 80% power?
            answerable = []
            if p_h1a >= 0.80:
                answerable.append("H1'a")
            if p_h1b_best >= 0.80:
                answerable.append(f"H1'b({best_tier})")
            if p_h2 >= 0.80:
                answerable.append("H2")
            answerable_str = ", ".join(answerable) if answerable else "(none at 80%)"

            results.append({
                "budget": budget,
                "tier_mix": "+".join(tier_mix),
                "n_per_cell": cfg.n_per_cell,
                "total_cost": cfg.total_cost,
                "total_rollouts": cfg.total_rollouts,
                "power_h1a_brier": p_h1a,
                "power_h1b_pass1_best_tier": p_h1b_best,
                "power_h1b_best_tier_name": best_tier,
                "power_h2_shadow": p_h2,
                "answerable": answerable_str,
            })
    return results


def print_table(results: list[dict]):
    print("=" * 110)
    print("Budget-Sensitivity Sweep — what does $X buy?")
    print("=" * 110)
    print(f"{'Budget':>10} {'Tier mix':>18} {'N/cell':>7} "
          f"{'Rollouts':>9} {'Actual$':>10} "
          f"{'H1a':>6} {'H1b':>10} {'H2':>6} {'Answerable @80%':>28}")
    print("-" * 110)
    last_budget = None
    for r in results:
        if r["budget"] != last_budget:
            print()  # separator between budget groups
            last_budget = r["budget"]
        tier_disp = r["tier_mix"].replace("haiku", "H").replace("sonnet", "S").replace("opus", "O")
        h1b_disp = f"{r['power_h1b_pass1_best_tier']:.2f}"
        if "power_h1b_best_tier_name" in r:
            h1b_disp += f"({r['power_h1b_best_tier_name'][0].upper()})"
        print(f"${r['budget']:>9,} {tier_disp:>18} "
              f"{r['n_per_cell']:>7} {r['total_rollouts']:>9} "
              f"${r['total_cost']:>9,.0f} "
              f"{r['power_h1a_brier']:>6.2f} "
              f"{h1b_disp:>10} "
              f"{r['power_h2_shadow']:>6.2f} "
              f"{r['answerable']:>28}")
    print("-" * 110)


def print_recommendations(results: list[dict]):
    # For each budget, find the tier-mix that maximizes # of answerable hypotheses
    by_budget: dict[int, list[dict]] = {}
    for r in results:
        by_budget.setdefault(r["budget"], []).append(r)

    print("\n" + "=" * 78)
    print("Recommendations by budget tier (max answerable hypotheses @80%)")
    print("=" * 78)

    def count_answerable(answerable_str: str) -> int:
        """Count real hypothesis labels, excluding error strings like '(none)'."""
        if not answerable_str or answerable_str.startswith("("):
            return 0
        return len([x for x in answerable_str.split(", ") if not x.startswith("(")])

    for budget, rs in sorted(by_budget.items()):
        # Score: number of real hypotheses answerable; tiebreak by N
        best = max(rs, key=lambda x: (
            count_answerable(x["answerable"]),
            x["n_per_cell"],
        ))
        print(f"\n  ${budget:,}  →  best config: tier_mix={best['tier_mix']}, N={best['n_per_cell']}")
        print(f"           answerable @80%: {best['answerable']}")
        print(f"           actual cost: ${best['total_cost']:,.0f} "
              f"({best['total_rollouts']:,} rollouts)")


def main():
    results = sweep()
    print_table(results)
    print_recommendations(results)

    print("\n" + "=" * 78)
    print("Interpretation (from actual sweep above)")
    print("=" * 78)
    print("* Under $5k: only H1'a (Brier-based calibration validity) reliably")
    print("  answerable. Workshop-paper territory.")
    print("")
    print("* $10-15k: Sonnet-only at N=500-800 answers H1'a + H1'b(sonnet).")
    print("  Single-tier calibration paper. Best cost-efficiency IF you don't")
    print("  care about shadow.")
    print("")
    print("* **$30k sweet spot:** 3-tier (H+S+O) at N=423 answers all three")
    print("  primary hypotheses: H1'a + H1'b(opus) + H2 shadow at 80% power.")
    print("  This is the minimum budget for a full scaffolding-shadow paper.")
    print("")
    print("* $50k: same 3-tier at N=706. Tighter CIs; H2 shadow power rises to")
    print("  ~84%. Comfortable primary venue submission.")
    print("")
    print("* $100-140k: 3-tier at N=1400-2000. Diminishing returns on answerability;")
    print("  improves precision only.")
    print("")
    print("KEY FINDING: the $140k figure was the ceiling for TIGHT CIs, not the")
    print("floor for ANSWERING THE QUESTION. At $30k you can still answer all")
    print("three primary hypotheses.")
    print("=" * 78)


if __name__ == "__main__":
    main()
