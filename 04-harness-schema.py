"""
Harness schema for the verifier-calibration experiment.

Defines the minimum structural contract between the agent loop, the verifier
module, and the telemetry system. This is not a full implementation — it is
the typed skeleton that pins the Harness Card from the protocol.

Design goals:
1. One file, one harness. Every experiment cell instantiates exactly one
   Harness object frozen by its Harness Card hash.
2. Observability is mandatory, not optional. Every tool call, every verifier
   output, every token count is logged with the harness_card_hash attached.
3. Verifier is a strict interface, not a prompt convention. Swapping verifier
   variants means swapping the Verifier implementation — nothing in the agent
   loop changes.
4. Failure-mode tagging happens on trajectory completion, not incrementally.
   Keeps the tagger uncoupled from the loop.

Python 3.12+, pydantic 2.x.
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


# =============================================================================
# Harness Card — frozen config contract (version-hashed)
# =============================================================================


class ToolAffordance(BaseModel):
    name: str
    description: str
    schema_hash: str  # hash of the JSON schema the tool accepts
    timeout_seconds: int = 60
    max_output_tokens: int = 4000


class ContextPolicy(BaseModel):
    max_context_tokens: int = 160_000
    # Canonical enum from 10-harness-card-template.md §H.4
    trimming_strategy: Literal["none", "fifo", "ledger", "semantic"] = "fifo"
    summarizer_model: str | None = None  # only for "semantic"
    keep_always: list[str] = Field(
        default_factory=lambda: ["system_prompt", "tool_schemas", "plan"]
    )
    plan_refresh_every_n_turns: int | None = 10


class MemoryPolicy(BaseModel):
    enabled: bool = False
    # Canonical enum from 10-harness-card-template.md §H.5
    write_gating: Literal["none", "all", "salience", "utility"] = "none"
    write_threshold: float | None = None  # only if salience-gated
    retrieval_top_k: int = 0
    retrieval_embedding_model: str | None = None
    max_memory_items: int | None = None
    eviction_rule: Literal["none", "lru", "lru_of_unused"] = "none"


class BudgetPolicy(BaseModel):
    max_turns: int = 50
    max_cost_usd: float = 5.00
    max_wall_seconds: int = 900  # 15 min hard stop


class PermissionPolicy(BaseModel):
    read_scope: Literal["repo", "repo+tmp", "unrestricted"] = "repo"
    write_scope: Literal["repo", "repo+tmp", "unrestricted"] = "repo"
    network: Literal["none", "package_install_only", "unrestricted"] = "package_install_only"
    destructive_op_gating: Literal["none", "confirm", "deny"] = "none"


class RecoveryPolicy(BaseModel):
    on_consecutive_failures: int = 3
    # Canonical enum per 10-harness-card-template.md §H.9
    on_failure_action: Literal["none", "plan_refresh", "rollback_and_replan", "escalate"] = "plan_refresh"
    circuit_breaker_rule: str | None = None
    rollback_granularity: Literal["none", "file", "repo"] | None = None


class VerifierCalibration(BaseModel):
    """Nested calibration block per template §H.6."""
    enabled: bool = False
    method: Literal["none", "temperature_scaling", "platt", "isotonic"] = "none"
    temperature: float | None = None
    calibration_set_description: str | None = None


class VerifierSpec(BaseModel):
    """Canonical verifier spec per template §H.6. `variant` is an experiment-cell
    label — not part of the generic Harness Card but useful when embedded in
    experiment-specific cards."""
    enabled: bool = False
    model: str | None = None
    prompt_hash: str | None = None
    calibration: VerifierCalibration = Field(default_factory=VerifierCalibration)
    decision_threshold: float | None = None
    # experiment-cell convenience label (optional, not canonical)
    variant: Literal["none", "weak-calibrated", "strong-uncalibrated", "strong-calibrated"] | None = None


class HarnessCard(BaseModel):
    """Frozen, hashable experiment cell definition."""

    name: str
    version: str
    base_model: str  # agent tier
    base_loop: Literal["react", "react+self-verify", "react+reflect"]
    tools: list[ToolAffordance]
    context_policy: ContextPolicy
    memory_policy: MemoryPolicy
    budget: BudgetPolicy
    permissions: PermissionPolicy
    recovery: RecoveryPolicy
    verifier: VerifierSpec

    def frozen_hash(self) -> str:
        """Merkle-style hash of the entire card. Attached to every logged step."""
        blob = json.dumps(self.model_dump(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


# =============================================================================
# Interfaces the experiment swaps between cells
# =============================================================================


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any]
    call_id: str


class ToolResult(BaseModel):
    call_id: str
    ok: bool
    output: str
    truncated: bool
    elapsed_seconds: float


class Tool(Protocol):
    name: str

    def call(self, args: dict[str, Any]) -> ToolResult: ...


class VerifierOutput(BaseModel):
    confidence: float  # 0.0-1.0, post-calibration
    raw_confidence: float  # 0.0-1.0, pre-calibration
    passes: bool
    reasoning: str


class Verifier(ABC):
    """Abstract verifier. Swap implementation per cell."""

    spec: VerifierSpec

    @abstractmethod
    def verify(
        self, task_description: str, trajectory: "Trajectory", final_diff: str
    ) -> VerifierOutput:
        ...


class NoneVerifier(Verifier):
    """Passes everything through unchanged; used when verifier is disabled."""

    def __init__(self, spec: VerifierSpec):
        self.spec = spec

    def verify(self, task_description: str, trajectory, final_diff: str) -> VerifierOutput:
        del task_description, trajectory, final_diff  # unused by design
        return VerifierOutput(
            confidence=1.0, raw_confidence=1.0, passes=True,
            reasoning="verifier disabled for this cell",
        )


# =============================================================================
# Trajectory — the unit of data we log, analyze, tag
# =============================================================================


class StepKind(str, Enum):
    THINK = "think"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    VERIFY = "verify"
    PLAN_REFRESH = "plan_refresh"
    TERMINATE = "terminate"


class TrajectoryStep(BaseModel):
    step_index: int
    kind: StepKind
    payload: dict[str, Any]
    tokens_in: int
    tokens_out: int
    cost_usd: float
    wall_seconds: float
    timestamp_unix: float


class FailureMode(str, Enum):
    """The 12-pattern taxonomy from 01-literature-map.md."""
    CONTEXT_ROT = "context_rot"
    TOOL_THRASH = "tool_thrash"
    PLAN_EXECUTION_DRIFT = "plan_execution_drift"
    RECOVERY_BLINDNESS = "recovery_blindness"
    RUBBER_STAMP_VERIFICATION = "rubber_stamp_verification"
    INSTRUCTION_BLEED = "instruction_bleed"
    CONFIDENCE_INVERSION = "confidence_inversion"
    SCAFFOLDING_SHADOW = "scaffolding_shadow"
    MEMORY_POLLUTION = "memory_pollution"
    BUDGET_MYOPIA = "budget_myopia"
    PERMISSION_LEARNED_HELPLESSNESS = "permission_learned_helplessness"
    OBSERVATION_COLLAPSE = "observation_collapse"
    OTHER = "other"


class TrajectoryOutcome(BaseModel):
    ground_truth_pass: bool  # from hidden tests
    verifier_pass: bool | None  # None if verifier=='none'
    final_diff: str
    turns_used: int
    cost_usd: float
    wall_seconds: float
    failure_mode_tag: FailureMode | None


class Trajectory(BaseModel):
    task_id: str
    cell_id: str  # {tier}×{verifier_variant}
    seed: int
    harness_card_hash: str
    steps: list[TrajectoryStep]
    outcome: TrajectoryOutcome


# =============================================================================
# Agent loop — the part that stays constant across experiment cells
# =============================================================================


class Task(BaseModel):
    task_id: str
    description: str
    repo_commit: str
    hidden_tests_path: str  # path to tests invisible to the agent


class LLMClient(Protocol):
    """Interface the AgentLoop uses to sample the next action. Production
    implementations wrap real provider APIs; tests use a deterministic stub."""

    def sample(self, prompt: str) -> "LLMResponse": ...


class LLMResponse(BaseModel):
    think: str
    action_kind: Literal["tool_call", "terminate", "plan_refresh"]
    tool_call: ToolCall | None = None
    final_diff: str | None = None
    plan_text: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


@dataclass
class AgentConfig:
    """Fully-wired config for running the loop — model name, harness card,
    verifier module, tool set, task definition, LLM client, and ground-truth
    oracle (invisible to the agent)."""
    model: str
    harness_card: HarnessCard
    verifier: Verifier
    tools: dict[str, Tool]
    task: "Task"
    llm: LLMClient
    ground_truth_oracle: "GroundTruthOracle"


class GroundTruthOracle(Protocol):
    """Runs the hidden tests against a final diff. Never exposed to the agent.
    In production: pytest against the task's hidden test suite. In tests: a
    scripted oracle that returns pass/fail for fake diffs."""

    def judge(self, task: "Task", final_diff: str) -> bool: ...


class AgentLoop:
    """The ReAct + self-verify loop. Same code across cells; verifier swapped.

    Concrete implementation: builds prompt, calls the LLM stub for each turn,
    dispatches tools, applies context trimming at each turn boundary, refreshes
    the plan on the configured cadence, invokes the verifier at termination,
    and emits a Trajectory.
    """

    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg
        self.steps: list[TrajectoryStep] = []
        self.context: list[dict[str, Any]] = []  # observation ledger
        self.plan: str = ""  # current plan text
        self._start_time = time.time()
        self._turns = 0

    # ----- budget & termination ------------------------------------------

    def _budget_exceeded(self) -> bool:
        elapsed = time.time() - self._start_time
        cost = sum(s.cost_usd for s in self.steps)
        return (
            elapsed > self.cfg.harness_card.budget.max_wall_seconds
            or cost > self.cfg.harness_card.budget.max_cost_usd
            or self._turns >= self.cfg.harness_card.budget.max_turns
        )

    # ----- context policy hook -------------------------------------------

    def _trim_context(self) -> None:
        """Apply the configured context-trimming strategy to self.context."""
        strategy = self.cfg.harness_card.context_policy.trimming_strategy
        if strategy == "none":
            return
        if strategy == "fifo":
            # Keep only the last 20 observations (matches spec)
            if len(self.context) > 20:
                self.context = self.context[-20:]
            return
        if strategy == "ledger":
            # Placeholder: extract structured facts, keep last 10 observations
            if len(self.context) > 10:
                self.context = self.context[-10:]
            return
        if strategy == "semantic":
            # Placeholder: would call summarizer_model; here we just keep last 5
            if len(self.context) > 5:
                self.context = self.context[-5:]
            return

    # ----- prompt building -----------------------------------------------

    def _build_prompt(self) -> str:
        """Assemble the agent's prompt from task + tools + plan + context.

        Context ordering: full-text for the most recent 3 observations (so the
        agent can actually use them), short summaries for the next 7 (so it
        knows they happened), older dropped entirely.
        """
        recent = self.context[-3:]
        older = self.context[-10:-3] if len(self.context) > 3 else []
        parts: list[str] = [
            f"Task: {self.cfg.task.description}",
            f"Tools available: {list(self.cfg.tools.keys())}",
            f"Current plan:\n{self.plan or '(no plan yet)'}",
            "",
            "Prior observations (older, summarized):",
        ]
        for o in older:
            parts.append(f"  - turn {o.get('turn')}: {o.get('summary', '')[:200]}")
        parts.extend(["", "Recent observations (full):"])
        for o in recent:
            parts.append(f"  --- turn {o.get('turn')} ---")
            parts.append(o.get('full', o.get('summary', '')))
        parts.extend(["", "Respond with your next action."])
        return "\n".join(parts)

    # ----- step emission -------------------------------------------------

    def _emit_step(self, kind: StepKind, payload: dict[str, Any],
                    tokens_in: int = 0, tokens_out: int = 0, cost: float = 0.0) -> None:
        self.steps.append(TrajectoryStep(
            step_index=len(self.steps), kind=kind, payload=payload,
            tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost,
            wall_seconds=time.time() - self._start_time,
            timestamp_unix=time.time(),
        ))

    # ----- main loop -----------------------------------------------------

    def run(self) -> Trajectory:
        final_diff: str | None = None
        termination_reason = "completed"

        while not self._budget_exceeded():
            self._turns += 1

            # Plan refresh on cadence
            refresh_every = self.cfg.harness_card.context_policy.plan_refresh_every_n_turns
            if refresh_every and self._turns > 1 and self._turns % refresh_every == 0:
                self._emit_step(StepKind.PLAN_REFRESH, {"before": self.plan})

            # LLM sample
            prompt = self._build_prompt()
            resp = self.cfg.llm.sample(prompt)
            self._emit_step(
                StepKind.THINK, {"think": resp.think},
                tokens_in=resp.tokens_in, tokens_out=resp.tokens_out, cost=resp.cost_usd,
            )

            # Apply the action
            if resp.action_kind == "plan_refresh":
                self.plan = resp.plan_text or self.plan
                continue

            if resp.action_kind == "terminate":
                final_diff = resp.final_diff or ""
                break

            # tool_call path
            if resp.tool_call is None:
                termination_reason = "malformed_action"
                break
            tool_name = resp.tool_call.tool
            if tool_name not in self.cfg.tools:
                self._emit_step(StepKind.TOOL_RESULT, {
                    "call_id": resp.tool_call.call_id,
                    "error": f"unknown tool: {tool_name}",
                })
                continue
            tool = self.cfg.tools[tool_name]
            self._emit_step(StepKind.TOOL_CALL, {
                "tool": tool_name, "args": resp.tool_call.arguments,
                "call_id": resp.tool_call.call_id,
            })
            result = tool.call(resp.tool_call.arguments)
            self._emit_step(StepKind.TOOL_RESULT, {
                "call_id": result.call_id, "ok": result.ok,
                "output": result.output, "truncated": result.truncated,
            })
            self.context.append({
                "turn": self._turns,
                "summary": result.output[:200],
                "full": result.output[:6000],
            })
            self._trim_context()
        else:
            termination_reason = "budget_exceeded"

        # Verifier invocation (even if no diff produced)
        verifier_out: VerifierOutput | None = None
        if self.cfg.harness_card.verifier.enabled:
            verifier_out = self.cfg.verifier.verify(
                self.cfg.task.description, None, final_diff or "",  # type: ignore[arg-type]
            )
            self._emit_step(StepKind.VERIFY, {
                "confidence": verifier_out.confidence,
                "passes": verifier_out.passes,
                "reasoning": verifier_out.reasoning,
            })

        # Ground truth
        gt_pass = (
            self.cfg.ground_truth_oracle.judge(self.cfg.task, final_diff or "")
            if final_diff is not None else False
        )

        self._emit_step(StepKind.TERMINATE, {"reason": termination_reason})

        outcome = TrajectoryOutcome(
            ground_truth_pass=gt_pass,
            verifier_pass=(verifier_out.passes if verifier_out else None),
            final_diff=final_diff or "",
            turns_used=self._turns,
            cost_usd=sum(s.cost_usd for s in self.steps),
            wall_seconds=time.time() - self._start_time,
            failure_mode_tag=None,  # post-hoc tagging by 11-failure-taxonomy-codebook
        )
        return Trajectory(
            task_id=self.cfg.task.task_id,
            cell_id=f"{self.cfg.model}_{self.cfg.harness_card.verifier.variant or 'none'}",
            seed=0,
            harness_card_hash=self.cfg.harness_card.frozen_hash(),
            steps=self.steps,
            outcome=outcome,
        )


# =============================================================================
# Test stubs — deterministic LLM and oracle for the end-to-end smoke test
# =============================================================================


class DeterministicLLM:
    """Scripted LLM stub: executes a fixed 4-turn trajectory on a fake task.

    Turn 1: plan
    Turn 2: tool call (search)
    Turn 3: tool call (edit)
    Turn 4: terminate with a "correct" diff
    """

    name = "deterministic-test-llm"

    def __init__(self):
        self._step = 0

    def sample(self, prompt: str) -> LLMResponse:
        self._step += 1
        if self._step == 1:
            return LLMResponse(
                think="I should plan before acting.", action_kind="plan_refresh",
                plan_text="1. Search for failing code\n2. Edit it\n3. Done",
                tokens_in=len(prompt) // 4, tokens_out=20, cost_usd=0.001,
            )
        if self._step == 2:
            return LLMResponse(
                think="Search for the failing function.",
                action_kind="tool_call",
                tool_call=ToolCall(
                    tool="search",
                    arguments={"query": "def broken"},
                    call_id=f"call_{self._step}",
                ),
                tokens_in=len(prompt) // 4, tokens_out=30, cost_usd=0.002,
            )
        if self._step == 3:
            return LLMResponse(
                think="Now edit the file with a fix.",
                action_kind="tool_call",
                tool_call=ToolCall(
                    tool="edit",
                    arguments={"path": "src/broken.py", "diff": "-return 0\n+return 1"},
                    call_id=f"call_{self._step}",
                ),
                tokens_in=len(prompt) // 4, tokens_out=40, cost_usd=0.003,
            )
        # Terminate
        return LLMResponse(
            think="Diff applied; submitting.",
            action_kind="terminate",
            final_diff="-return 0\n+return 1",
            tokens_in=len(prompt) // 4, tokens_out=15, cost_usd=0.001,
        )


class FakeSearchTool:
    name = "search"

    def call(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            call_id=args.get("__call_id", "search_result"),
            ok=True,
            output=f"Found 2 matches for '{args.get('query', '')}'",
            truncated=False, elapsed_seconds=0.05,
        )


class FakeEditTool:
    name = "edit"

    def call(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            call_id=args.get("__call_id", "edit_applied"),
            ok=True,
            output=f"Applied diff to {args.get('path', 'unknown')}",
            truncated=False, elapsed_seconds=0.02,
        )


class ScriptedOracle:
    """Returns pass/fail based on whether the diff contains '+return 1'."""

    def judge(self, task: Task, final_diff: str) -> bool:
        del task  # unused in this stub; real oracle would run hidden tests
        return "+return 1" in final_diff


class ScriptedVerifier(Verifier):
    """Verifier stub: agrees when the diff contains the expected fix."""

    def __init__(self, spec: VerifierSpec):
        self.spec = spec

    def verify(self, task_description: str, trajectory, final_diff: str) -> VerifierOutput:
        del task_description, trajectory  # unused in this stub
        has_fix = "+return 1" in final_diff
        return VerifierOutput(
            confidence=0.9 if has_fix else 0.3,
            raw_confidence=0.9 if has_fix else 0.3,
            passes=has_fix,
            reasoning=f"Diff contains expected fix: {has_fix}",
        )


# =============================================================================
# Example: instantiate a Harness Card for one experiment cell
# =============================================================================


def example_card_opus_strong_calibrated() -> HarnessCard:
    """The Opus / strong-calibrated cell of the factorial."""
    return HarnessCard(
        name="vcal-swebench-opus-strongcal",
        version="1.0",
        base_model="claude-opus-4-7",
        base_loop="react+self-verify",
        tools=[
            ToolAffordance(
                name="shell", description="non-interactive bash",
                schema_hash="sha256:abc123", timeout_seconds=60,
                max_output_tokens=4000,
            ),
            ToolAffordance(
                name="edit", description="unified-diff apply",
                schema_hash="sha256:def456", timeout_seconds=10,
                max_output_tokens=500,
            ),
            ToolAffordance(
                name="search", description="ripgrep wrapper",
                schema_hash="sha256:789abc", timeout_seconds=15,
                max_output_tokens=8000,
            ),
            ToolAffordance(
                name="run_tests", description="pytest runner",
                schema_hash="sha256:fedcba", timeout_seconds=300,
                max_output_tokens=4000,
            ),
        ],
        context_policy=ContextPolicy(
            max_context_tokens=160_000, trimming_strategy="fifo",
            plan_refresh_every_n_turns=10,
        ),
        memory_policy=MemoryPolicy(enabled=False),
        budget=BudgetPolicy(max_turns=50, max_cost_usd=5.00, max_wall_seconds=900),
        permissions=PermissionPolicy(
            read_scope="repo+tmp", write_scope="repo",
            network="package_install_only", destructive_op_gating="none",
        ),
        recovery=RecoveryPolicy(
            on_consecutive_failures=3, on_failure_action="plan_refresh",
        ),
        verifier=VerifierSpec(
            enabled=True,
            model="claude-opus-4-7",
            prompt_hash="sha256:verifier_prompt_v1_placeholder",
            calibration=VerifierCalibration(
                enabled=True,
                method="temperature_scaling",
                temperature=1.37,  # hypothetical fitted value
                calibration_set_description="50 SWE-bench Lite held-out tasks",
            ),
            decision_threshold=0.5,
            variant="strong-calibrated",
        ),
    )


def run_end_to_end_smoke_test() -> Trajectory:
    """Wire up a full AgentLoop with deterministic stubs and run one task."""
    card = example_card_opus_strong_calibrated()
    # Override context trimming to fifo for deterministic behavior in this test
    task = Task(
        task_id="smoke-001",
        description="Fix the broken() function to return 1 instead of 0",
        repo_commit="deadbeef",
        hidden_tests_path="/tmp/test_broken.py",
    )
    cfg = AgentConfig(
        model="test-stub",
        harness_card=card,
        verifier=ScriptedVerifier(card.verifier),
        tools={"search": FakeSearchTool(), "edit": FakeEditTool()},  # type: ignore[dict-item]
        task=task,
        llm=DeterministicLLM(),
        ground_truth_oracle=ScriptedOracle(),
    )
    loop = AgentLoop(cfg)
    traj = loop.run()
    return traj


if __name__ == "__main__":
    card = example_card_opus_strong_calibrated()
    print(f"Harness Card:  {card.name} v{card.version}")
    print(f"Frozen hash:   {card.frozen_hash()}")
    print(f"Verifier:      {card.verifier.variant} ({card.verifier.model})")
    print(f"Budget:        {card.budget.max_turns} turns / "
          f"${card.budget.max_cost_usd:.2f} / "
          f"{card.budget.max_wall_seconds}s")
    print(f"Tools:         {[t.name for t in card.tools]}")

    print("\n" + "=" * 60)
    print("End-to-end smoke test of AgentLoop")
    print("=" * 60)
    traj = run_end_to_end_smoke_test()
    print(f"Task:              {traj.task_id}")
    print(f"Cell:              {traj.cell_id}")
    print(f"Harness hash:      {traj.harness_card_hash}")
    print(f"Turns used:        {traj.outcome.turns_used}")
    print(f"Steps emitted:     {len(traj.steps)}")
    print(f"Cost (stub):       ${traj.outcome.cost_usd:.4f}")
    print(f"Final diff:        {traj.outcome.final_diff!r}")
    print(f"Ground truth pass: {traj.outcome.ground_truth_pass}")
    print(f"Verifier pass:     {traj.outcome.verifier_pass}")
    print("\nStep trace:")
    for s in traj.steps:
        print(f"  [{s.step_index:2d}] {s.kind.value:14s}  {list(s.payload.keys())}")
