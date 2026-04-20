# Failure-Mode Taxonomy — Coding Rubric v1.0

*A structured rubric for tagging failed agent trajectories into the 12-pattern
failure taxonomy. Designed to achieve inter-rater κ > 0.70 when used by trained
coders (human or LLM).*

---

## Purpose

Every agent experiment in this research program tags each failed trajectory
with **exactly one primary failure mode** plus zero or more secondary tags.
Consistent coding is essential for the cross-protocol meta-analysis.

This rubric is derived from the 12-pattern taxonomy in `01-literature-map.md`
(Claude's brainstorm contribution) and operationalizes each pattern into
decidable criteria.

---

## Usage

For each failed trajectory (ground_truth_pass == false):

1. Read the final diff + last 20 turns.
2. Walk the rubric top-down. Assign the *first* matching primary tag.
3. Note any secondary patterns observed.
4. If no pattern matches, assign `OTHER` with a one-sentence explanation.

Human coder target: ~3 min per trajectory.
LLM coder target: ~30 sec per trajectory.

---

## The 12 Primary Tags (decision order)

### 1. TOOL_THRASH

**Definition.** Agent oscillates between 2-3 tool calls without state progress.

**Decidable criteria (ALL must hold):**
- ≥ 4 tool calls in the last 10 turns where ≥ 75% similarity (by args) to a prior
  call in the same trajectory.
- No net state change observed between these calls (same file version, same test
  state, same search results).
- Task remains unsolved at termination.

**Distinguishing from LOOP_TRAPS (general):** tool thrash specifically involves
oscillation between *different* calls; loop trap is the general case including
identical repetition. Tool thrash is the *cyclic* subtype.

**Example.**
```
Turn 10: search("LoginError")
Turn 11: read_file("auth.py", 1-50)
Turn 12: search("LoginError")  ← repeat
Turn 13: read_file("auth.py", 1-50)  ← repeat
Turn 14: search("LoginError")
```

### 2. PLAN_EXECUTION_DRIFT

**Definition.** The plan written early (turn ≤ 5) no longer describes what the
agent is doing at a later turn, but the agent still cites or references the plan.

**Decidable criteria (ALL):**
- Plan exists in trajectory (plan tag or structured plan output).
- At turn N (N ≥ 15), agent's actions are unrelated to ≥ 50% of plan steps.
- Agent still references "the plan" without updating it.

**Distinguishing from CONTEXT_ROT:** drift is about *executed* steps diverging
from *stated* plan; context rot is about the agent losing the goal from attention,
not from a specific plan statement.

**Example.**
```
Turn 3 plan: [a. Fix the migration bug; b. Add tests; c. Update docs]
Turn 20 action: refactoring an unrelated config file, says "continuing plan step b"
```

### 3. CONTEXT_ROT

**Definition.** Global coherence decay after long context; agent's current
action is incompatible with turn-1 goal, not due to a specific bad plan.

**Decidable criteria (ALL):**
- Trajectory length > 20 turns.
- At termination, the final diff is unrelated to the task description (judged
  by independent LLM on a contrastive prompt).
- No identifiable plan-drift event (distinguishes from #2).

**Signature heuristic:** ask the judge "in the last 5 turns, does the agent
mention the original task at all?" If no → rot.

**Example.**
```
Task: fix a failing database test
Final diff: updates README formatting, unrelated to database
```

### 4. OBSERVATION_COLLAPSE

**Definition.** A multi-page tool output is summarized (by the agent or by a
trimming policy) into a single sentence that loses key detail needed in a later step.

**Decidable criteria (ALL):**
- Tool output at turn K contains > 500 tokens.
- Agent's next-turn response or summary contains < 100 tokens referring to it.
- At turn K+M (M ≥ 3), agent needs information from turn K that was dropped.
- Missing information is identifiable in the original output.

**Example.**
```
Turn 5 search returns 40-line results; agent says "found several matches"
Turn 12 agent asks "what file was the auth function in?" — info dropped at turn 5
```

### 5. RECOVERY_BLINDNESS

**Definition.** Agent enters a bad state (failed test, error response) and
does not detect it or replan; continues as if on track.

**Decidable criteria (ALL):**
- At least one tool response indicates failure (non-zero exit, test failure,
  error string) at turn K.
- Agent's turn K+1 action does not acknowledge failure (no retry, no plan update,
  no diagnostic step).
- Task ultimately fails.

**Note:** distinguishes from PLAN_EXECUTION_DRIFT: drift is about plan-vs-action
mismatch; recovery blindness is about failure-vs-next-step mismatch.

**Example.**
```
Turn 8 run_tests: "FAILED: test_auth"
Turn 9 agent: "Tests pass. Moving to next step."
```

### 6. RUBBER_STAMP_VERIFICATION

**Definition.** Verifier returns "pass" / high-confidence on a trajectory that
in fact fails ground truth.

**Decidable criteria (ALL):**
- Verifier was invoked (verifier_condition != none).
- Verifier output: `passes=true` or `confidence > 0.7`.
- Ground truth: fail.
- Verifier reasoning does not cite any specific evidence in the trajectory
  that would support its judgment (judged by independent audit).

**Operationalization:** for the verifier-calibration protocol, any rollout where
`verifier_pass == true` but `ground_truth_pass == false` AND verifier reasoning
lacks trajectory-specific citation is tagged rubber-stamp.

### 7. CONFIDENCE_INVERSION

**Definition.** Agent expresses high confidence at termination but the task is
in fact incorrect. Distinguishes from rubber-stamp (verifier-based) — this is
about the *agent's* self-declared confidence.

**Decidable criteria (ALL):**
- Agent's final utterance contains a confident claim ("this should work",
  "all tests pass", "the fix is complete").
- Ground truth: fail.
- No detected hedging ("might", "should", "hopefully") in the final utterance.

### 8. INSTRUCTION_BLEED

**Definition.** A system-prompt or task-description instruction is silently
ignored by turn N.

**Decidable criteria (ALL):**
- Task or system prompt contains a specific instruction (e.g., "do not modify
  tests", "use Python 3.12 syntax").
- Trajectory violates the instruction.
- Agent does not acknowledge the violation.

**Example.**
```
Instruction: "do not modify tests"
Turn 15: agent edits test_auth.py
```

### 9. MEMORY_POLLUTION

**Definition (only applicable when memory enabled).** Retrieved memory misleads
the agent.

**Decidable criteria (ALL):**
- Memory retrieval occurred at turn K.
- Agent's turn K+1 action used the retrieved memory (quoted or referenced).
- The retrieved memory was wrong or irrelevant for the current task.
- Task subsequently fails in a way attributable to the bad memory.

### 10. BUDGET_MYOPIA

**Definition.** Budget exhausted before solving a task that would have been
solvable with better budget allocation.

**Decidable criteria (ALL):**
- Termination reason: budget exhaustion (not voluntary finish).
- Last 25% of budget was spent on a single non-productive phase (e.g., many
  consecutive searches without progress, or redundant verification).
- An oracle judge (retrospective LLM) says "better budget allocation would
  plausibly have solved this."

### 11. PERMISSION_LEARNED_HELPLESSNESS

**Definition (only applicable with permission-gated tools).** One tool call
denied; agent stops attempting any tool calls when variants would have been
allowed.

**Decidable criteria (ALL):**
- At turn K, a tool call returned a permission-denied error.
- Agent's turns K+1..K+5 do not attempt any tool call at all, OR attempt only
  the exact same denied call.
- A permitted variant exists that would have accomplished the same goal.

### 12. SCAFFOLDING_SHADOW (meta tag)

**Definition.** A failure mode that only manifests at a higher model tier; a
symptom of harness defects surfaced by capability.

**Decidable criteria (ALL):**
- The same task succeeds at a weaker model tier under the same harness
  (observed in a parallel cell of the experiment).
- The failure is not attributable to any of tags 1-11.
- The failure appears specific to behaviors that the stronger model generates
  (e.g., more complex plans, novel tool combinations).

**Note.** This tag is *experiment-specific* — can only be assigned when cross-tier
data is available. It is the meta-pattern.

### OTHER

Use when none of the 12 apply. Include a one-sentence description.

Target OTHER rate: < 10% of failures. If > 10%, the taxonomy is missing a
pattern — escalate for review.

---

## Secondary (Multi-Tag) Flags

Trajectories often exhibit multiple patterns. Coders may assign secondary tags
(up to 3) from the same 12-tag set in addition to the primary. Secondary tags
are reported but do not count toward the primary-tag distribution.

---

## Inter-Rater Agreement Protocol

1. **Training.** 3 sessions of 10 trajectories, coders review disagreements,
   rubric clarified.
2. **Measurement.** 50 trajectories double-coded by two independent coders.
   Compute Cohen's κ.
3. **Target.** κ > 0.70 overall. Individual-tag κ reported separately; tags with
   κ < 0.5 flagged for rubric revision.
4. **LLM coder validation.** LLM-based auto-coder calibrated against 100-trajectory
   human-coded reference; target LLM-vs-human κ > 0.70 before deploying at scale.

---

## Reporting

Each experiment paper reports:

1. Distribution of primary tags per cell (fraction of failures that are
   CONTEXT_ROT, TOOL_THRASH, etc.).
2. Shift in distribution across conditions (does verifier reduce RUBBER_STAMP?
   does adaptive budget reduce BUDGET_MYOPIA?).
3. OTHER rate per cell (as a rubric-quality check).
4. Inter-rater κ.

---

## Example Coded Trajectory

```yaml
trajectory_id: opus_V3_task_0042_seed_1
ground_truth_pass: false
primary_failure_mode: RUBBER_STAMP_VERIFICATION
secondary_flags: [PLAN_EXECUTION_DRIFT]
coder_notes: >
  Verifier returned confidence 0.85; diff introduces subtle off-by-one in
  pagination. Plan at turn 3 said "add pagination"; actual diff changed sort
  order instead.
coded_by: human_coder_A (+ lmjudge_v2 agreement)
```

---

## Rubric Revision Log

- v1.0 (2026-04-20): initial rubric. Derived from 12-pattern taxonomy in
  literature map.
- Future revisions: track major changes here.
