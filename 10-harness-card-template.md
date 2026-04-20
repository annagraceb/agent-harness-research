# The Harness Card Standard — v1.0 Proposal

*A lightweight reporting standard for agent experiments. Analogous to Model Cards
(Mitchell et al. 2019) and Data Sheets for Datasets (Gebru et al. 2018). Required
field set designed to be small enough to include in a paper appendix, detailed
enough to support replication.*

---

## Why Harness Cards

The "scaffolding shadow" finding — that harness quality interacts with model
capability — implies that a score on a benchmark like SWE-bench is
*uninterpretable* without the harness spec that produced it. Two labs reporting
`pass@1 = 45%` on SWE-bench Verified may have radically different systems.

The Harness Card is a machine-readable, human-auditable artifact that resolves
this. It travels with the paper, the dataset release, and the leaderboard entry.

---

## Required Fields (v1.0)

### H.1 — Identity

```yaml
identity:
  name: str  # human-readable name, e.g., "vcal-swebench-v1"
  version: str  # semver
  paper: str  # arxiv / doi if published
  authors: list[str]
  frozen_hash: str  # SHA-256 of this card (16-hex prefix min) — computed, not hand-edited
```

### H.2 — Base Model(s)

```yaml
base_model:
  provider: str  # e.g., "anthropic", "openai", "meta"
  model_id: str  # exact API or weight identifier
  version_snapshot_date: str  # ISO-8601 — when the model was queried
  temperature: float
  max_output_tokens: int
  top_p: float | null
  other_sampling_params: dict  # any additional provider-specific params
```

**Rationale.** Vendor models drift silently. The `version_snapshot_date` disambiguates
"Opus 4.7 on 2026-03-05" from "Opus 4.7 on 2026-04-01" — they may produce different
results.

### H.3 — Tools

```yaml
tools:
  - name: str
    description: str  # the description shown to the model
    input_schema_hash: str  # sha256 of the JSON schema (for exact replication)
    timeout_seconds: int
    max_output_tokens: int
    affordance_notes: str  # e.g., "ripgrep --count -only, truncates at 200 matches"
```

**Rationale.** Two tools named "search" can behave entirely differently. The
schema hash + affordance notes pin the tool contract.

### H.4 — Context Policy (D1)

```yaml
context_policy:
  max_context_tokens: int
  trimming_strategy: enum  # none | fifo | ledger | semantic
  summarizer_model: str | null  # only for semantic trimming
  kept_always: list[str]  # e.g., ["system_prompt", "tool_schemas", "plan"]
  plan_refresh_every_n_turns: int | null
```

### H.5 — Memory Policy (D3)

```yaml
memory_policy:
  enabled: bool
  write_gating: enum  # none | all | salience | utility
  write_threshold: float | null  # if salience-gated
  retrieval_top_k: int
  retrieval_embedding_model: str | null
  max_memory_items: int | null
  eviction_rule: enum  # lru | lru_of_unused | none
```

### H.6 — Verification Policy (D4)

```yaml
verifier:
  enabled: bool
  model: str | null
  prompt_hash: str | null  # sha256 of the verifier prompt template
  calibration:
    enabled: bool
    method: enum | null  # none | temperature_scaling | platt | isotonic
    temperature: float | null
    calibration_set_description: str | null
  decision_threshold: float | null
```

### H.7 — Budget Policy (D5)

```yaml
budget:
  max_turns: int
  max_cost_usd: float
  max_wall_seconds: int
  allocation_strategy: enum  # fixed_uniform | fixed_frontloaded | adaptive
  phase_allocations: dict | null  # only if adaptive
```

### H.8 — Permission Model (D6)

```yaml
permissions:
  read_scope: enum  # repo | repo+tmp | unrestricted
  write_scope: enum
  network: enum  # none | package_install_only | unrestricted
  destructive_op_gating: enum  # none | confirm | deny
  sandbox_runtime: str  # docker image ID, firejail profile, etc.
```

### H.9 — Recovery Policy (D7)

```yaml
recovery:
  on_consecutive_failures: int
  on_failure_action: enum  # none | plan_refresh | rollback_and_replan | escalate
  circuit_breaker_rule: str | null  # e.g., ">90% similarity to failed call in last 5 turns"
  rollback_granularity: enum | null  # none | file | repo
```

### H.10 — Evaluation Methodology

```yaml
evaluation:
  benchmark: str  # e.g., "SWE-bench Verified @ 2024-10-release"
  benchmark_snapshot_hash: str | null
  split: str  # "verified", "lite", "full"
  tasks_used: int
  seeds_per_task: int
  metrics_reported: list[str]  # e.g., ["pass@1", "pass^3"]
  per_task_timeout_minutes: int
```

### H.11 — Reproducibility

```yaml
reproducibility:
  harness_code_url: str | null  # git URL + commit hash
  license: str
  logs_released: bool
  trajectories_released: bool
  compute_cost_usd: float | null
  approx_wallclock_hours: float | null
```

### H.12 — Changelog

```yaml
changelog:
  - version: str
    date: str
    changes: str
```

---

## Minimum Viable Card (paper-appendix friendly)

Labs may want a *short* card in the main text and a *full* card in the appendix.
The minimum viable Harness Card is:

```
Harness: {name} v{version}  [hash: {frozen_hash}]
Model:   {base_model.model_id} @ {version_snapshot_date}
Tools:   {N tools} — [{tool names}]
Context: {trimming_strategy}, max={max_context_tokens} tok
Memory:  {enabled/disabled} [{gating}]
Verify:  {enabled/disabled} [{model} {calibration.method}]
Budget:  {max_turns} turns / ${max_cost_usd} / {max_wall_seconds}s
Perms:   {read_scope}/{write_scope} net={network}
Recover: {on_failure_action}@{on_consecutive_failures}
Bench:   {benchmark} N={tasks_used} seeds={seeds_per_task}
```

This is ~12 lines, fits in a paper's methods section, and uniquely identifies
the harness via its hash.

---

## Validation Rules

A Harness Card is **valid** iff:

1. `frozen_hash` matches the SHA-256 of the entire card (minus the hash field
   itself) with fields sorted alphabetically.
2. Every `*_hash` field matches the actual hash of the referenced artifact.
3. All `enum` fields take values from the defined enum set.
4. `version_snapshot_date` is ISO-8601 and not in the future.
5. If `verifier.enabled == true`, `verifier.model` is non-null.
6. If `memory.enabled == true`, `memory.write_gating != "none"`.

Machine-checkable via `harness_card.validate()` in the reference implementation.

---

## Reference Implementation

`04-harness-schema.py` in this directory is the reference implementation as
pydantic models. It produces canonical JSON serialization for hashing.

---

## Adoption Path

**Phase 1 (proposal):** Propose as a standard at a workshop (e.g., Agent4All, LLM
Agents workshop at NeurIPS). Solicit feedback from 5-10 major labs.

**Phase 2 (reference):** Publish reference implementation + validator + 3
worked examples (verifier protocol, context protocol, memory protocol from this
research program).

**Phase 3 (incentive):** Encourage benchmark hosts (SWE-bench, τ-bench, OSWorld)
to require Harness Card submission alongside leaderboard entries. Cards become
leaderboard metadata.

**Phase 4 (norm):** Papers publishing agent results without a Harness Card are
flagged by reviewers as non-replicable. Adoption becomes norm within ~2 years
(similar timeline to Model Cards).

---

## Objections and Responses

**"This is too much paperwork."**
The minimum viable card is 12 lines. The full card is one YAML file. Labs
currently waste more time re-deriving scaffold details from prose descriptions.

**"Harnesses are moving too fast to standardize."**
v1.0 captures 7 well-established dimensions. Future versions can add fields
without breaking existing cards (cards are forward-compatible via the
`changelog` field).

**"What about proprietary harnesses?"**
Even proprietary labs benefit from internal standardization. A Harness Card
can be published with sensitive fields (prompts, custom tools) redacted as
hash-only references.

**"This just adds one more thing to read."**
Reviewers benefit directly: currently impossible to tell if paper X and paper Y
are comparable. Harness Cards make the answer obvious at a glance.

---

## Example: Full Card for the Verifier Protocol

```yaml
identity:
  name: vcal-swebench
  version: 1.0
  paper: arxiv:2026.XXXXX
  authors: [Anna Grace Bentley]
  frozen_hash: "to-be-computed"
base_model:
  provider: anthropic
  model_id: claude-opus-4-7
  version_snapshot_date: "2026-04-01"
  temperature: 0.0
  max_output_tokens: 8192
  top_p: null
  other_sampling_params: {}
tools:
  - name: shell
    description: non-interactive bash, 60s timeout
    input_schema_hash: "sha256:abc..."
    timeout_seconds: 60
    max_output_tokens: 4000
    affordance_notes: "Runs in repo-rooted Docker sandbox"
  # ... 3 more tools
context_policy:
  max_context_tokens: 160000
  trimming_strategy: fifo
  summarizer_model: null
  kept_always: [system_prompt, tool_schemas, plan]
  plan_refresh_every_n_turns: 10
memory_policy:
  enabled: false
  write_gating: none
  write_threshold: null
  retrieval_top_k: 0
  retrieval_embedding_model: null
  max_memory_items: null
  eviction_rule: none
verifier:
  enabled: true
  model: claude-opus-4-7
  prompt_hash: "sha256:ver..."
  calibration:
    enabled: true
    method: temperature_scaling
    temperature: 1.37
    calibration_set_description: "50 SWE-bench Lite tasks, held out"
  decision_threshold: 0.5
budget:
  max_turns: 50
  max_cost_usd: 5.00
  max_wall_seconds: 900
  allocation_strategy: fixed_uniform
  phase_allocations: null
permissions:
  read_scope: repo+tmp
  write_scope: repo
  network: package_install_only
  destructive_op_gating: none
  sandbox_runtime: "docker:swebench-eval:v4"
recovery:
  on_consecutive_failures: 3
  on_failure_action: plan_refresh
  circuit_breaker_rule: null
  rollback_granularity: none
evaluation:
  benchmark: "SWE-bench Verified"
  benchmark_snapshot_hash: "sha256:..."
  split: verified
  tasks_used: 750
  seeds_per_task: 3
  metrics_reported: [pass@1, pass^3, Brier_score]
  per_task_timeout_minutes: 15
reproducibility:
  harness_code_url: "git://github.com/user/vcal@abc123"
  license: Apache-2.0
  logs_released: true
  trajectories_released: true
  compute_cost_usd: 53100
  approx_wallclock_hours: 280
changelog:
  - version: "1.0"
    date: "2026-04-20"
    changes: "initial release"
```

---

## Open Questions (for community discussion)

- Should Harness Cards include a **failure-mode fingerprint** (rate per failure
  mode) as part of the card, to enable at-a-glance comparison?
- How should **multi-agent harnesses** (agent teams) be described? v1.0 assumes
  single-agent; v2.0 extension needed.
- How should **online harnesses** (real web, real APIs) be reproducibly cited
  when upstream state drifts? Suggestion: Wayback Machine snapshots + timestamp
  intervals.
