"""
Meta-analysis stub — reference implementation for 19-meta-analysis-protocol.md.

Takes per-protocol trajectory.jsonl files and produces:
  - meta_results.json: per-dimension R(t), shadow-gradient γ_d, meta-hypothesis tests
  - shadow_fingerprint.png: the 3-panel figure (Panel A curves, B bars, C heatmap)
  - tables.tex: publication-ready LaTeX tables

Until real pilot data is available, this script runs on *synthetic* per-protocol
output that matches the expected schema. When real data is in, replace the
`generate_synthetic_trajectories()` call with a `load_trajectories(path)` call.

Run:  python3 22-meta-analysis-stub.py
Deps: pandas, numpy, matplotlib (all already present in this environment)
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any

RNG = np.random.default_rng(20260420)
OUT_DIR = Path("/home/cisco/agent-harness-research")


# -----------------------------------------------------------------------------
# Schema (mirrors 04-harness-schema.py Trajectory)
# -----------------------------------------------------------------------------


DIMENSIONS = ["D1_context", "D3_memory", "D4_verifier", "D5_budget"]
TIERS = ["haiku", "sonnet", "opus"]

# Per-dimension level set (maps the actual IV1 of each upstream protocol)
DIMENSION_LEVELS = {
    "D1_context":  ["none", "fifo", "ledger", "semantic"],
    "D3_memory":   ["none", "all", "salience", "utility"],
    "D4_verifier": ["none", "weak-cal", "strong-uncal", "strong-cal"],
    "D5_budget":   ["fixed-uniform", "fixed-frontloaded",
                    "adaptive-self", "adaptive-oracle"],
}

# Per-dimension predicted primary failure modes (per 19-protocol §B)
PREDICTED_PRIMARY_FAILURE = {
    "D1_context":  ["context_rot", "observation_collapse"],
    "D3_memory":   ["memory_pollution"],
    "D4_verifier": ["rubber_stamp_verification"],
    "D5_budget":   ["budget_myopia", "tool_thrash"],
}


# -----------------------------------------------------------------------------
# Synthetic data generator — stands in for real pilot data
# -----------------------------------------------------------------------------


# Pre-registered priors with built-in scaffolding-shadow pattern
# (R_opus > R_sonnet > R_haiku for each dimension)
SYNTHETIC_PRIORS = {
    "D1_context": {
        "haiku":  {"none": 0.09, "fifo": 0.13, "ledger": 0.13, "semantic": 0.12},
        "sonnet": {"none": 0.25, "fifo": 0.37, "ledger": 0.39, "semantic": 0.38},
        "opus":   {"none": 0.32, "fifo": 0.57, "ledger": 0.62, "semantic": 0.64},
    },
    "D3_memory": {
        "haiku":  {"none": 0.13, "all": 0.12, "salience": 0.13, "utility": 0.14},
        "sonnet": {"none": 0.37, "all": 0.33, "salience": 0.38, "utility": 0.42},
        "opus":   {"none": 0.57, "all": 0.50, "salience": 0.59, "utility": 0.65},
    },
    "D4_verifier": {
        "haiku":  {"none": 0.10, "weak-cal": 0.13, "strong-uncal": 0.11, "strong-cal": 0.15},
        "sonnet": {"none": 0.32, "weak-cal": 0.37, "strong-uncal": 0.30, "strong-cal": 0.40},
        "opus":   {"none": 0.52, "weak-cal": 0.57, "strong-uncal": 0.49, "strong-cal": 0.60},
    },
    "D5_budget": {
        # BrowseComp, different absolute scale
        "haiku":  {"fixed-uniform": 0.15, "fixed-frontloaded": 0.17,
                    "adaptive-self": 0.16, "adaptive-oracle": 0.18},
        "sonnet": {"fixed-uniform": 0.32, "fixed-frontloaded": 0.36,
                    "adaptive-self": 0.34, "adaptive-oracle": 0.39},
        "opus":   {"fixed-uniform": 0.48, "fixed-frontloaded": 0.54,
                    "adaptive-self": 0.52, "adaptive-oracle": 0.58},
    },
}


def generate_synthetic_trajectories(n_per_cell: int = 500) -> pd.DataFrame:
    """Emit a long-form DataFrame matching the expected trajectory.jsonl schema.

    One row per rollout, columns: [dimension, tier, level, task_id, seed,
    ground_truth_pass, verifier_pass, cost_usd, failure_mode_tag].
    """
    rows: list[dict[str, Any]] = []
    for dim in DIMENSIONS:
        for tier in TIERS:
            for level in DIMENSION_LEVELS[dim]:
                p = SYNTHETIC_PRIORS[dim][tier][level]
                for task_id in range(n_per_cell):
                    for seed in range(3):
                        gt = RNG.random() < p
                        # Failure-mode tag — align with predicted primaries
                        if gt:
                            tag = None
                        else:
                            primaries = PREDICTED_PRIMARY_FAILURE[dim]
                            # 60% of failures are predicted-primary, 40% other
                            if RNG.random() < 0.6:
                                tag = RNG.choice(primaries)
                            else:
                                tag = RNG.choice([
                                    "tool_thrash", "plan_execution_drift",
                                    "instruction_bleed", "confidence_inversion",
                                    "other",
                                ])
                        rows.append({
                            "dimension": dim,
                            "tier": tier,
                            "level": level,
                            "task_id": f"{dim}_t{task_id:04d}",
                            "seed": seed,
                            "ground_truth_pass": bool(gt),
                            "verifier_pass": bool(gt),  # not used for meta-analysis
                            "cost_usd": 0.0,
                            "failure_mode_tag": str(tag) if tag else None,
                        })
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Meta-analysis computations
# -----------------------------------------------------------------------------


def compute_cell_pass1(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse to per-cell pass@1 = mean(any-seed-success per task)."""
    per_task = (
        df.groupby(["dimension", "tier", "level", "task_id"])
          .agg(any_pass=("ground_truth_pass", "any"))
          .reset_index()
    )
    cells = (
        per_task.groupby(["dimension", "tier", "level"])
                .agg(pass_at_1=("any_pass", "mean"),
                     n=("any_pass", "count"))
                .reset_index()
    )
    return cells


def compute_range_per_tier(cells: pd.DataFrame) -> pd.DataFrame:
    """R(tier) = max_level pass@1 - min_level pass@1, per (dim, tier)."""
    agg = (
        cells.groupby(["dimension", "tier"])
             .agg(R=("pass_at_1", lambda x: x.max() - x.min()))
             .reset_index()
    )
    return agg


def compute_shadow_gradient(ranges: pd.DataFrame,
                              tier_capability: dict[str, float]) -> pd.DataFrame:
    """γ_d = Cov(R_d(tier), capability(tier)) / Var(capability)."""
    out = []
    cap_vals = np.array([tier_capability[t] for t in TIERS])
    for dim in DIMENSIONS:
        r_vals = np.array([
            ranges[(ranges["dimension"] == dim) & (ranges["tier"] == t)]["R"].iloc[0]
            for t in TIERS
        ])
        slope, intercept = np.polyfit(cap_vals, r_vals, 1)
        out.append({
            "dimension": dim,
            "gamma_d": slope,
            "intercept": intercept,
            "R_haiku": r_vals[0], "R_sonnet": r_vals[1], "R_opus": r_vals[2],
            "delta_R": r_vals[2] - r_vals[0],
            "shadow_positive": slope > 0,
        })
    return pd.DataFrame(out)


def meta_hypothesis_m1(gradients: pd.DataFrame) -> dict[str, Any]:
    """M1: shadow positive in ≥ 3 of 4 dimensions."""
    n_positive = int(gradients["shadow_positive"].sum())
    supported = n_positive >= 3
    return {"hypothesis": "M1_general_shadow", "n_positive": n_positive,
            "total": len(gradients), "supported": supported}


def meta_hypothesis_m2(gradients: pd.DataFrame) -> dict[str, Any]:
    """M2: CV(ΔR_d) ≤ 0.5."""
    delta: np.ndarray = np.asarray(gradients["delta_R"].values, dtype=float)
    mean_d = float(np.mean(delta))
    std_d = float(np.std(delta))
    cv = std_d / max(mean_d, 1e-9)
    supported = cv <= 0.5
    return {"hypothesis": "M2_magnitude_invariance", "CV": cv,
            "mean_delta_R": mean_d, "std_delta_R": std_d,
            "supported": supported}


def meta_hypothesis_m3(df: pd.DataFrame) -> dict[str, Any]:
    """M3: per-dimension modal failure mode matches prediction."""
    results = []
    for dim in DIMENSIONS:
        fails = df[(df["dimension"] == dim) & (df["failure_mode_tag"].notna())]
        if len(fails) == 0:
            continue
        mode_series = fails["failure_mode_tag"].mode()
        mode = str(mode_series.iloc[0]) if len(mode_series) > 0 else "unknown"
        predicted = PREDICTED_PRIMARY_FAILURE[dim]
        matches = mode in predicted
        results.append({"dimension": dim, "observed_mode": mode,
                         "predicted_modes": predicted, "matches": matches})
    n_matches = sum(r["matches"] for r in results)
    return {"hypothesis": "M3_failure_fingerprint", "per_dim": results,
            "n_matches": n_matches, "total": len(results),
            "supported": n_matches >= 3}


# -----------------------------------------------------------------------------
# Figure stub (3 panels)
# -----------------------------------------------------------------------------


def make_fingerprint_figure(ranges: pd.DataFrame, gradients: pd.DataFrame,
                              df: pd.DataFrame, outpath: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Panel A — per-dim shadow curves
    ax = axes[0]
    tier_x = np.arange(3)
    for dim in DIMENSIONS:
        r_vals = [
            ranges[(ranges["dimension"] == dim) & (ranges["tier"] == t)]["R"].iloc[0]
            for t in TIERS
        ]
        ax.plot(tier_x, r_vals, marker="o", label=dim)
    ax.set_xticks(tier_x)
    ax.set_xticklabels(TIERS)
    ax.set_ylabel("R(tier) = range of pass@1 across levels")
    ax.set_title("Panel A — Shadow curves per dimension")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)

    # Panel B — ΔR_d bar chart
    ax = axes[1]
    dims = gradients["dimension"].values
    deltas = gradients["delta_R"].values
    ax.bar(range(len(dims)), deltas)
    ax.set_xticks(range(len(dims)))
    ax.set_xticklabels(dims, rotation=15)
    ax.set_ylabel("ΔR_d = R(opus) - R(haiku)")
    ax.set_title("Panel B — Shadow magnitude per dimension")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.grid(alpha=0.3)

    # Panel C — failure-mode fingerprint heatmap (dim × failure-mode)
    ax = axes[2]
    failure_modes = sorted(df[df["failure_mode_tag"].notna()]["failure_mode_tag"].unique())
    heat = np.zeros((len(DIMENSIONS), len(failure_modes)))
    for i, dim in enumerate(DIMENSIONS):
        fails = df[(df["dimension"] == dim) & (df["failure_mode_tag"].notna())]
        total = len(fails)
        if total == 0:
            continue
        for j, fm in enumerate(failure_modes):
            heat[i, j] = (fails["failure_mode_tag"] == fm).sum() / total
    im = ax.imshow(heat, aspect="auto", cmap="Blues")
    ax.set_xticks(range(len(failure_modes)))
    ax.set_xticklabels(failure_modes, rotation=45, ha="right")
    ax.set_yticks(range(len(DIMENSIONS)))
    ax.set_yticklabels(DIMENSIONS)
    ax.set_title("Panel C — Failure-mode fingerprint")
    fig.colorbar(im, ax=ax, label="rate")

    plt.tight_layout()
    plt.savefig(outpath, dpi=120, bbox_inches="tight")
    plt.close()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def run() -> None:
    print("=" * 72)
    print("Meta-Analysis Stub — runs on synthetic data")
    print("=" * 72)

    df = generate_synthetic_trajectories(n_per_cell=500)
    print(f"\nGenerated {len(df):,} synthetic rollouts across "
          f"{len(DIMENSIONS)} dimensions × {len(TIERS)} tiers.")

    cells = compute_cell_pass1(df)
    print("\nPer-cell pass@1 (head):")
    print(cells.head(8).to_string(index=False))

    ranges = compute_range_per_tier(cells)
    print("\nPer-tier R(tier) (full):")
    print(ranges.to_string(index=False))

    # Use no-verifier haiku pass@1 as "capability" proxy for meta-regression
    tier_capability = {}
    for t in TIERS:
        # Proxy: average no-level pass@1 across dimensions
        try:
            vals = cells[(cells["tier"] == t) & (cells["level"].isin(
                ["none", "fixed-uniform"]))]["pass_at_1"].mean()
            tier_capability[t] = float(vals)
        except Exception:
            tier_capability[t] = {"haiku": 0.1, "sonnet": 0.3, "opus": 0.5}[t]

    print(f"\nTier capability proxy: {tier_capability}")

    gradients = compute_shadow_gradient(ranges, tier_capability)
    print("\nShadow gradients per dimension:")
    print(gradients.to_string(index=False))

    m1 = meta_hypothesis_m1(gradients)
    m2 = meta_hypothesis_m2(gradients)
    m3 = meta_hypothesis_m3(df)

    print("\n" + "-" * 72)
    print("Meta-hypothesis tests (synthetic):")
    print("-" * 72)
    for mh in [m1, m2, m3]:
        print(f"  {mh['hypothesis']}: supported={mh['supported']}")
        for k, v in mh.items():
            if k in ("hypothesis", "supported", "per_dim"):
                continue
            print(f"    {k}: {v}")

    # Save meta-results
    meta_results = {
        "generated_at": "2026-04-20T12:20Z",
        "synthetic_data": True,
        "n_rollouts": len(df),
        "per_tier_ranges": ranges.to_dict(orient="records"),
        "shadow_gradients": gradients.to_dict(orient="records"),
        "m1": m1, "m2": m2, "m3": m3,
    }
    out_json = OUT_DIR / "meta_results_synthetic.json"
    with out_json.open("w") as f:
        json.dump(meta_results, f, indent=2, default=str)
    print(f"\nSaved: {out_json}")

    # Produce fingerprint figure
    fig_path = OUT_DIR / "shadow_fingerprint_synthetic.png"
    make_fingerprint_figure(ranges, gradients, df, fig_path)
    print(f"Saved: {fig_path}")

    print("\n" + "=" * 72)
    print("This stub runs on synthetic data. When real pilot data is in,")
    print("replace generate_synthetic_trajectories() with a real loader:")
    print("  trajectories = [Trajectory.parse_raw(line)")
    print("                  for line in open('protocol_X_trajectories.jsonl')]")
    print("  df = pd.DataFrame([t.dict() for t in trajectories])")
    print("=" * 72)


if __name__ == "__main__":
    run()
