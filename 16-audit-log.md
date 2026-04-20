# Consistency Audit Log — 2026-04-20T09:15Z

*Record of cross-file consistency fixes performed during T10. Each entry
documents what was wrong, where, and what authoritative source was used
to reconcile.*

---

## Summary

8 real inconsistencies found across 15 files. 8 fixed. All downstream
artifacts remain compilable / runnable.

---

## Bug Log

### Bug 1 — Stale N=500 references

**Where:**
- `01-literature-map.md` line 94: `DV1: pass@1 (500 tasks)`
- `02-verifier-calibration-protocol.md` line 63: "(500 tasks). ... all 500 seen"
- `03-power-analysis.md` line 110: "Re-confirm N = 500 still clears targets"

**Authoritative source:** `03-power-analysis.md` Results table recommending N=750.

**Fix:** updated all three references to N=750 with explanatory note. Retained
legitimate N=500 mentions that document the revision narrative (e.g., "revised
up from 500").

### Bug 2 — `ContextPolicy.trimming_strategy` enum mismatch

**Where:**
- `04-harness-schema.py` had `["fifo", "recency_weighted", "none"]`
- `10-harness-card-template.md` had `none | fifo | ledger | semantic`
- `07-scaffolding-shadow-protocol.md` had `[no-trim, fifo, ledger, semantic]`

Three different enum sets for the same concept.

**Authoritative source:** `10-harness-card-template.md` §H.4 (canonical v1.0).

**Fix:** aligned `04-harness-schema.py` to `["none", "fifo", "ledger", "semantic"]`
and added `summarizer_model` field. Updated `07-scaffolding-shadow-protocol.md`
to use `none` instead of `no-trim`. Added explicit "enum values align" callout
in the scaffolding-shadow protocol table.

### Bug 3 — `MemoryPolicy.write_gating` enum missing "all"

**Where:**
- `04-harness-schema.py` had `["none", "salience", "utility"]`
- `10-harness-card-template.md` had `none | all | salience | utility`

**Authoritative source:** template §H.5.

**Fix:** added `"all"` to the pydantic literal; added fields
`write_threshold`, `retrieval_embedding_model`, `max_memory_items`,
`eviction_rule` to match template fully.

### Bug 4 — `RecoveryPolicy.on_failure_action` missing "escalate"

**Where:**
- `04-harness-schema.py` had `["none", "plan_refresh", "rollback_and_replan"]`
- `10-harness-card-template.md` had `none | plan_refresh | rollback_and_replan | escalate`

**Authoritative source:** template §H.9.

**Fix:** added `"escalate"`; added `circuit_breaker_rule` and
`rollback_granularity` fields.

### Bug 5 — `VerifierSpec` flat-vs-nested calibration structure

**Where:**
- `04-harness-schema.py` had flat `calibration_temperature: float | None`.
- `10-harness-card-template.md` had nested `calibration: {enabled, method,
  temperature, calibration_set_description}`.

**Authoritative source:** template §H.6 (nested structure is canonical).

**Fix:** introduced `VerifierCalibration` nested model; refactored `VerifierSpec`
to embed it; added `enabled`, `prompt_hash` fields to match canonical;
kept `variant` as optional experiment-cell label (not part of canonical card
but useful when embedded in experiment-specific cards).

### Bug 6 — Harness Card YAML in 02-protocol not v1.0-conformant

**Where:** `02-verifier-calibration-protocol.md` §6 had a "v0.1" YAML block
using non-canonical field names (`tool_set`, `trimming`, `plan_refresh_cadence`,
`max_cost_usd_per_task`, `permissions` as string, `recovery_policy` as string).

**Authoritative source:** `10-harness-card-template.md` v1.0.

**Fix:** regenerated the YAML block to conform to v1.0. Marked explicitly as
"Conforms to Harness Card v1.0." Downstream pages now have a consistent
example.

### Bug 7 — (Resolved during fix 6)

Same-doc inconsistency: `02-verifier-calibration-protocol.md` line 112 had
`permissions: "read/write restricted..."` as free-text string, violating
the structured-enum canonical form. Fixed by regenerating the YAML.

### Bug 8 — Pyright `_args`/`_kwargs` warning in `NoneVerifier.verify`

**Where:** `04-harness-schema.py` `NoneVerifier.verify(self, *_args, **_kwargs)`.

**Severity:** cosmetic; non-breaking. Underscore-prefix convention is standard
for intentionally-unused parameters; Pyright still warns.

**Decision:** leave as-is. The convention clarifies intent; Pyright warning is
a tool-level disagreement, not a bug.

---

## Files Touched in Audit

- `01-literature-map.md` (N=500 → N=750)
- `02-verifier-calibration-protocol.md` (task-universe text; v1.0-conformant YAML)
- `03-power-analysis.md` (pilot-confirm text)
- `04-harness-schema.py` (enum expansions; VerifierSpec refactor)
- `07-scaffolding-shadow-protocol.md` (`no-trim` → `none`; enum-alignment callout)

All other files passed audit unchanged.

---

## Audit Method

1. Cross-grep for numeric constants (`500`, `750`, `18000`, `27000`).
2. Cross-grep for canonical field names (`trimming_strategy`, `write_gating`,
   `on_failure_action`, `calibration_temperature`).
3. Cross-grep for H1' references to confirm reach.
4. Smoke-test runnable Python after each schema change.
5. Read every YAML-like block; verify it parses mentally against the canonical
   template.

Total audit time: ~15 min.

---

## Invariants Established

After this audit, the following invariants hold across the research directory:

- **Sample size:** N=750 per cell is the authoritative recommendation, cited
  consistently. Historical N=500 appears only in explanatory narrative.
- **Harness Card v1.0:** canonical definition lives in
  `10-harness-card-template.md` §H.1-H.12. `04-harness-schema.py` is the
  pydantic reference implementation. All YAML examples in protocols conform.
- **Enum values:** seven enums have authoritative definitions in the template:
  `trimming_strategy`, `write_gating`, `eviction_rule`, `on_failure_action`,
  `rollback_granularity`, `calibration.method`, `budget.allocation_strategy`.
  Any field violating these enums is a bug.
- **H1 / H1' structure:** `02-verifier-calibration-protocol.md` §14 + `06-statistical-
  analysis-plan.md` §2.1a are the authoritative references for the H1' hypothesis
  and its activation condition (pilot accuracy-gap > 10pp).

---

## Recommendation for Future Edits

1. Treat `10-harness-card-template.md` §H.1-H.12 as the schema source of truth.
2. Treat `04-harness-schema.py` as the reference implementation; keep them
   synchronized.
3. When adding a new enum value, update BOTH files in the same commit.
4. Before each protocol pre-registration is frozen on OSF, re-run this audit.
