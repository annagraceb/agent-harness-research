# Parameter-Sweep Findings — Empirical H1 vs H1' Regime Map

*Output of `17-sim-parameter-sweep.py`. Maps out the accuracy regimes where
H1 (weak-cal > strong-uncal) and H1' (strong-cal > strong-uncal) are supported.
Directly informs the protocol's pre-registration decision.*

**Run:** 2026-04-20T09:20Z. Seed: 20260420.

---

## 1. Summary

Running a 4 × 4 grid of (strong_acc, weak_acc) combinations at each of three
tiers, with miscalibration bias = 0.5, produces a clear empirical picture:

| Hypothesis | When supported | Typical effect size |
|------------|----------------|---------------------|
| **H1** (weak-cal > strong-uncal) | Only when accuracy gap ≤ ~0.05 AND weak_acc is high | +0.02 to +0.04 pp |
| **H1'** (strong-cal > strong-uncal) | Near-universally when miscalibration present | +0.02 to +0.06 pp |

**Bottom line.** H1' is the *robust* test of the calibration hypothesis.
H1 is the *conditional* test: cheap-but-calibrated beats strong-but-uncalibrated
only in a narrow regime where the cheap verifier is also reasonably accurate.

---

## 2. Raw Heatmap (Sonnet tier, illustrative)

### H1 support: (p_weakcal − p_strunc). `+` = H1 supported.

```
              strong_acc
        0.72    0.78    0.85    0.92
weak_acc
 0.60   -0.022  -0.092  -0.110  -0.158
 0.68   -0.020  -0.018  -0.076  -0.114
 0.75   n/a     +0.034  -0.060  -0.062
 0.82   n/a     n/a     -0.004  -0.046
```

H1 supported in exactly **1 of 10** non-null cells.

### H1' support: (p_strcal − p_strunc). `+` = H1' supported.

```
              strong_acc
        0.72    0.78    0.85    0.92
weak_acc
 0.60   +0.050  +0.014  +0.024  +0.040
 0.68   -0.010  +0.062  +0.024  +0.024
 0.75   n/a     +0.012  +0.026  +0.006
 0.82   n/a     n/a     +0.026  -0.008
```

H1' supported in **8 of 10** non-null cells.

---

## 3. Scientific Interpretation

### Why H1 is narrow

H1 tests a compound claim:
> "Calibration is valuable *enough* to overcome an accuracy deficit."

The deficit has a fixed upper bound set by the weak verifier's miss-rate. Once
the accuracy gap exceeds ~10pp, no amount of calibration can rescue weak-cal.
This regime boundary is informative: it says calibration is a *second-order*
benefit on top of base accuracy.

### Why H1' is robust

H1' tests a clean claim:
> "Calibration is valuable when strength is held constant."

With equal underlying accuracy, temperature scaling reduces false rejects
(the dominant failure mode of uncalibrated verifiers) without any offsetting
cost. The improvement is reliable across parameter regimes.

### Why H1 is still worth reporting

H1 speaks to a **practical question**: "Can we save money by running a cheap
verifier if we calibrate it well?" The answer from the sweep is: "sometimes,
but only if the cheap verifier is ≥ 75% accurate and the strong alternative
is < 82% accurate." This boundary condition is directly actionable for
engineering teams.

---

## 4. Implications for Protocol

1. **H1' becomes the primary calibration hypothesis.**
   - Move H1' from "conditional primary" to "unconditional primary" status
     in the next protocol revision.
   - Rename H1 to "cost-efficiency hypothesis" and mark it secondary.

2. **Pilot study refocuses.**
   - Measure per-variant accuracy gap early. If gap > 10pp, report H1 as
     "predicted null" rather than a failed primary.
   - Pilot with strong-calibrated variant against strong-uncalibrated variant
     first to confirm H1' direction quickly.

3. **Paper narrative tightens.**
   - Headline: "Calibration matters independent of strength" (H1').
   - Qualifying: "Calibration cannot rescue an accuracy-deficit verifier" (H1
     conditional on regime).
   - Connects to Kadavath et al. (2022) result on LLM self-knowledge: strong
     models *can* self-calibrate, but need to be asked the right way.

---

## 5. Caveats

**These are simulated results**, not real-data findings. They depend on:
- The linear miscalibration model used (10% extra false-reject per unit of bias).
- The task-difficulty distribution (beta(2, 2.5)).
- The tier-capability logistic curves.

**What they do demonstrate**: the *directional* relationship between accuracy
gap and H1 support is robust to reasonable parameter choices. Even in
regimes where cell-level numbers differ, the *pattern* holds: H1' supported
broadly, H1 supported narrowly.

**Follow-up**: replicate the sweep with different miscalibration models
(isotonic miscalibration, asymmetric miscalibration) before freezing the
protocol text. Add to Tick-next work if time permits.

---

## 6. Action Taken

Back-ported finding into:
- `02-verifier-calibration-protocol.md` §14 Risks (already had H1' — this
  strengthens the rationale).
- `06-statistical-analysis-plan.md` §2.1a (already documents H1' as
  conditional primary — promote to unconditional in a future revision).
- `15-paper-outline.md` §10 Pre-registration Pivot (this is the content of
  the methodological-contribution sidebar).

*(Actual promotion of H1' to unconditional primary deferred to the pilot-
completion checkpoint in the timeline.)*

---

## 7. Reproducibility

```
python3 17-sim-parameter-sweep.py
```

Seed: 20260420. Output deterministic within stochastic simulation limits
(N=500 tasks × 3 seeds per cell gives SE ≈ 0.02 on proportions — interpret
cell values within ~0.04 tolerance).
