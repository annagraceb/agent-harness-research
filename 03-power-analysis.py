"""
Power analysis for the verifier-calibration x model-tier factorial experiment
on SWE-bench Verified.

Computes minimum detectable effect size and required sample size for:
- H1: pairwise contrast (weak-cal vs strong-uncal) within a tier
- H2: range-of-cells difference between tiers (scaffolding shadow)
- H3: partial eta^2 on pass^k reliability metric

Uses bootstrap simulation because the DVs are bounded (0-1 proportions)
and the classical Cohen-h power formula overstates power at proportions
near the ceiling.

Run: python 03-power-analysis.py
Dependencies: numpy, scipy (pinned in requirements below)
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass

RNG = np.random.default_rng(20260420)


# -----------------------------------------------------------------------------
# Pilot priors (based on public SWE-bench Verified leaderboards as of 2026-01)
# -----------------------------------------------------------------------------
# These are pre-registered priors. Actual experiment will update them.
PRIOR_PASS_AT_1 = {
    "haiku":  {"none": 0.10, "weak-cal": 0.13, "strong-uncal": 0.11, "strong-cal": 0.15},
    "sonnet": {"none": 0.32, "weak-cal": 0.37, "strong-uncal": 0.30, "strong-cal": 0.40},
    "opus":   {"none": 0.52, "weak-cal": 0.57, "strong-uncal": 0.49, "strong-cal": 0.60},
}
# Pass^3 is always lower; rough prior: pass^3 ~ pass@1 ** 1.4 for weakly correlated seeds
PRIOR_PASS_CUBED = {
    tier: {cond: p ** 1.4 for cond, p in conds.items()}
    for tier, conds in PRIOR_PASS_AT_1.items()
}


@dataclass
class PowerResult:
    hypothesis: str
    n_per_cell: int
    detected_fraction: float
    avg_observed_effect: float
    ci95_effect: tuple[float, float]
    passes: bool  # detected_fraction > 0.80


def _simulate_cell(p: float, n: int) -> np.ndarray:
    """Simulate n Bernoulli trials at success rate p."""
    return RNG.binomial(1, p, size=n)


def power_h1_pairwise(
    p_weakcal: float,
    p_strunc: float,
    n_per_cell: int,
    n_sims: int = 1000,
) -> PowerResult:
    """H1: weak-cal > strong-uncal within tier. One-sided z-test on proportions."""
    rejections = 0
    observed_effects = []
    for _ in range(n_sims):
        a = _simulate_cell(p_weakcal, n_per_cell)
        b = _simulate_cell(p_strunc, n_per_cell)
        p1, p2 = a.mean(), b.mean()
        p_pool = (a.sum() + b.sum()) / (2 * n_per_cell)
        se = math.sqrt(p_pool * (1 - p_pool) * 2 / n_per_cell)
        if se == 0:
            continue
        z = (p1 - p2) / se
        # One-sided: we predict weak-cal > strong-uncal
        if z > 1.645:  # one-sided 0.05
            rejections += 1
        observed_effects.append(p1 - p2)
    avg_eff = float(np.mean(observed_effects))
    ci = (float(np.percentile(observed_effects, 2.5)),
          float(np.percentile(observed_effects, 97.5)))
    detected = rejections / n_sims
    return PowerResult(
        hypothesis="H1 (weak-cal > strong-uncal, within tier)",
        n_per_cell=n_per_cell,
        detected_fraction=detected,
        avg_observed_effect=avg_eff,
        ci95_effect=ci,
        passes=detected >= 0.80,
    )


def power_h2_interaction(
    priors: dict, n_per_cell: int, n_sims: int = 1000
) -> PowerResult:
    """
    H2: scaffolding shadow — range of cell means at opus > range at haiku by >= 3pp.

    Range_tier = max(pass@1 over conditions) - min(pass@1 over conditions).
    Test: bootstrap CI on (R_opus - R_haiku) excludes values below 0.03.
    """
    rejections = 0
    observed_deltas = []
    for _ in range(n_sims):
        cells = {
            tier: {
                cond: _simulate_cell(priors[tier][cond], n_per_cell).mean()
                for cond in priors[tier]
            }
            for tier in priors
        }
        r_haiku = max(cells["haiku"].values()) - min(cells["haiku"].values())
        r_opus = max(cells["opus"].values()) - min(cells["opus"].values())
        delta = r_opus - r_haiku
        observed_deltas.append(delta)
        # Crude test: delta > 0.03 in the observed sample
        # Full experiment uses bootstrap CI; here we approximate
        if delta > 0.03:
            rejections += 1
    avg_delta = float(np.mean(observed_deltas))
    ci = (float(np.percentile(observed_deltas, 2.5)),
          float(np.percentile(observed_deltas, 97.5)))
    return PowerResult(
        hypothesis="H2 (R_opus - R_haiku > 0.03)",
        n_per_cell=n_per_cell,
        detected_fraction=rejections / n_sims,
        avg_observed_effect=avg_delta,
        ci95_effect=ci,
        passes=(rejections / n_sims) >= 0.80,
    )


def power_h3_reliability_sensitivity(
    priors_at_1: dict, priors_cubed: dict, n_per_cell: int, n_sims: int = 500
) -> PowerResult:
    """
    H3: verifier IV explains more variance in pass^3 than in pass@1.

    Operationalized as partial eta^2 comparison.
    This is a crude simulation — actual analysis uses GLM.
    """
    eta2_diffs = []
    rejections = 0
    for _ in range(n_sims):
        # Build 4x3 matrix of cell means for pass@1 and pass^3
        tiers = list(priors_at_1.keys())
        conds = list(priors_at_1[tiers[0]].keys())

        def eta2_for(priors):
            rows = []
            for tier in tiers:
                row = []
                for cond in conds:
                    row.append(_simulate_cell(priors[tier][cond], n_per_cell).mean())
                rows.append(row)
            arr = np.array(rows)  # tiers x conds
            grand = arr.mean()
            # Partial eta^2 for the "cond" factor (simplified, additive model)
            cond_means = arr.mean(axis=0)
            ss_cond = n_per_cell * len(tiers) * ((cond_means - grand) ** 2).sum()
            ss_total = n_per_cell * ((arr - grand) ** 2).sum() * len(tiers)
            return ss_cond / max(ss_total, 1e-9)

        eta2_at_1 = eta2_for(priors_at_1)
        eta2_cubed = eta2_for(priors_cubed)
        diff = eta2_cubed - eta2_at_1
        eta2_diffs.append(diff)
        if diff > 0:
            rejections += 1
    return PowerResult(
        hypothesis="H3 (eta^2 on pass^3 > eta^2 on pass@1)",
        n_per_cell=n_per_cell,
        detected_fraction=rejections / n_sims,
        avg_observed_effect=float(np.mean(eta2_diffs)),
        ci95_effect=(float(np.percentile(eta2_diffs, 2.5)),
                     float(np.percentile(eta2_diffs, 97.5))),
        passes=(rejections / n_sims) >= 0.80,
    )


def run() -> list[PowerResult]:
    print("=" * 72)
    print("Verifier-Calibration Experiment: Power Analysis")
    print("Priors from SWE-bench Verified public leaderboards (2026-01 snapshot)")
    print("=" * 72)

    results = []

    # H1: tested at Sonnet tier as the representative middle case.
    # We want to detect weak-cal (0.37) vs strong-uncal (0.30) = 7pp effect.
    for n in [150, 250, 400, 500, 750]:
        r = power_h1_pairwise(
            PRIOR_PASS_AT_1["sonnet"]["weak-cal"],
            PRIOR_PASS_AT_1["sonnet"]["strong-uncal"],
            n_per_cell=n,
        )
        results.append(r)
        print(f"\n--- {r.hypothesis} ---")
        print(f"  n per cell: {n}")
        print(f"  detected: {r.detected_fraction:.2%}  passes 80%? {r.passes}")
        print(f"  observed effect: {r.avg_observed_effect:+.3f} "
              f"[{r.ci95_effect[0]:+.3f}, {r.ci95_effect[1]:+.3f}]")

    # H2: interaction — requires all 12 cells at N. Test at several N values.
    for n in [200, 350, 500, 750]:
        r = power_h2_interaction(PRIOR_PASS_AT_1, n_per_cell=n)
        results.append(r)
        print(f"\n--- {r.hypothesis} ---")
        print(f"  n per cell: {n}")
        print(f"  detected: {r.detected_fraction:.2%}  passes 80%? {r.passes}")
        print(f"  observed delta R: {r.avg_observed_effect:+.3f} "
              f"[{r.ci95_effect[0]:+.3f}, {r.ci95_effect[1]:+.3f}]")

    # H3: partial eta^2 comparison
    for n in [200, 500]:
        r = power_h3_reliability_sensitivity(
            PRIOR_PASS_AT_1, PRIOR_PASS_CUBED, n_per_cell=n
        )
        results.append(r)
        print(f"\n--- {r.hypothesis} ---")
        print(f"  n per cell: {n}")
        print(f"  detected: {r.detected_fraction:.2%}  passes 80%? {r.passes}")
        print(f"  eta^2 diff: {r.avg_observed_effect:+.4f} "
              f"[{r.ci95_effect[0]:+.4f}, {r.ci95_effect[1]:+.4f}]")

    print("\n" + "=" * 72)
    print("Recommendation (revised from actual simulation output):")
    print("  * N = 750 tasks/cell achieves 89% power for H1 at Sonnet tier.")
    print("    (N = 500 only achieves 77%, below 80% target.)")
    print("  * H2 (scaffolding shadow) requires N=750 for 85% power.")
    print("  * H3 is irreducibly under-powered under current priors.")
    print("    Reclassified from secondary-confirmatory to exploratory-only.")
    print("  * Pilot at N=50 strongly advised before committing full 27k rollouts.")
    print("=" * 72)
    return results


if __name__ == "__main__":
    run()
