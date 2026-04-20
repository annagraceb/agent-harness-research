"""
Frugal runtime — HumanEvalFix loader + sandboxed tools + ground-truth oracle
+ end-to-end runner for the AgentLoop from 04-harness-schema.py.

This is the part that turns the adapter (27-ollama-adapter.py) into a real
running agent on real tasks. Combined with 27-ollama-adapter.py, this gives
us:

  Task (HumanEvalFix)
     ↓
  AgentLoop (04-harness-schema.py)  ← OllamaLLM (27-ollama-adapter.py)
     ↓
  real sandboxed tools (this file)
     ↓
  ground-truth oracle (this file)
     ↓
  Trajectory

Run smoke test:  python3 28-frugal-runtime.py
Requires: Ollama daemon, at least one model, `datasets`, `pytest` (or stdlib).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Load the schema contract
_schema_path = Path(__file__).resolve().parent / "04-harness-schema.py"
_schema_spec = importlib.util.spec_from_file_location("harness_schema", str(_schema_path))
assert _schema_spec and _schema_spec.loader
harness_schema = importlib.util.module_from_spec(_schema_spec)
sys.modules["harness_schema"] = harness_schema
_schema_spec.loader.exec_module(harness_schema)

Task = harness_schema.Task
AgentConfig = harness_schema.AgentConfig
AgentLoop = harness_schema.AgentLoop
ToolResult = harness_schema.ToolResult
Trajectory = harness_schema.Trajectory

# Load the Ollama adapter
_adapter_path = Path(__file__).resolve().parent / "27-ollama-adapter.py"
_adapter_spec = importlib.util.spec_from_file_location("ollama_adapter", str(_adapter_path))
assert _adapter_spec and _adapter_spec.loader
ollama_adapter = importlib.util.module_from_spec(_adapter_spec)
sys.modules["ollama_adapter"] = ollama_adapter
_adapter_spec.loader.exec_module(ollama_adapter)

OllamaLLM = ollama_adapter.OllamaLLM


SANDBOX_ROOT = Path("/tmp/frugal-runs")
SANDBOX_ROOT.mkdir(exist_ok=True)


# =============================================================================
# HumanEvalFix task model
# =============================================================================


@dataclass
class HumanEvalFixTask:
    """A HumanEvalFix task wrapped with everything the runner needs."""
    task_id: str           # e.g. "Python/0"
    declaration: str       # imports + signature
    buggy_solution: str    # the body with a bug
    canonical_solution: str  # the correct body (NEVER shown to agent)
    test: str              # the check() function (NEVER shown to agent)
    entry_point: str       # function name
    docstring: str = ""
    instruction: str = ""

    def buggy_file_contents(self) -> str:
        return self.declaration + self.buggy_solution + "\n"

    def canonical_file_contents(self) -> str:
        return self.declaration + self.canonical_solution + "\n"

    def test_harness(self) -> str:
        """Full test script: the check() function + an invocation."""
        return (
            self.test
            + f"\n\ncheck({self.entry_point})\n"
            + "print('TESTS_PASSED')\n"
        )

    def as_schema_task(self) -> Task:
        """Convert to a harness_schema.Task for the AgentLoop."""
        return Task(
            task_id=self.task_id,
            description=(
                f"Fix the bug in the function `{self.entry_point}` in "
                f"`solution.py`.\n\n"
                f"The function should satisfy its docstring. Use the tools to "
                f"read the file, edit it, and run the tests. When tests pass, "
                f"submit your final solution as the contents of `solution.py`."
            ),
            repo_commit="humanevalfix-public",
            hidden_tests_path="(internal)",
        )


def load_humanevalfix(limit: int | None = None) -> list[HumanEvalFixTask]:
    """Load HumanEvalFix tasks from HuggingFace bigcode/humanevalpack."""
    from datasets import load_dataset  # local import to keep module-import fast
    ds = load_dataset("bigcode/humanevalpack", "python", split="test")
    out: list[HumanEvalFixTask] = []
    for row in ds:
        out.append(HumanEvalFixTask(
            task_id=row["task_id"],
            declaration=row["declaration"],
            buggy_solution=row["buggy_solution"],
            canonical_solution=row["canonical_solution"],
            test=row["test"],
            entry_point=row["entry_point"],
            docstring=row.get("docstring", ""),
            instruction=row.get("instruction", ""),
        ))
        if limit is not None and len(out) >= limit:
            break
    return out


# =============================================================================
# Sandbox
# =============================================================================


@dataclass
class Sandbox:
    task_id: str
    seed: int
    path: Path = field(init=False)

    def __post_init__(self):
        safe = self.task_id.replace("/", "_")
        self.path = SANDBOX_ROOT / f"{safe}_seed{self.seed}"
        self.path.mkdir(parents=True, exist_ok=True)

    def setup(self, task: HumanEvalFixTask) -> None:
        """Write the initial (buggy) state into the sandbox."""
        (self.path / "solution.py").write_text(task.buggy_file_contents())

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


# =============================================================================
# Sandboxed tools
# =============================================================================


@dataclass
class ReadFileTool:
    name: str = "read_file"
    sandbox: Sandbox | None = None

    def call(self, args: dict[str, Any]) -> ToolResult:
        path = args.get("path", "solution.py")
        target = (self.sandbox.path / path) if self.sandbox else Path(path)
        call_id = f"read_{time.time_ns()}"
        try:
            contents = target.read_text()
            return ToolResult(
                call_id=call_id, ok=True,
                output=contents[:8000],
                truncated=len(contents) > 8000, elapsed_seconds=0.01,
            )
        except FileNotFoundError:
            return ToolResult(
                call_id=call_id, ok=False,
                output=f"File not found: {path}",
                truncated=False, elapsed_seconds=0.01,
            )


@dataclass
class EditFileTool:
    """Replaces file contents entirely. Accepts either a `contents` arg (full
    replacement) or a `body` arg (body of the target function; we prepend the
    declaration automatically)."""
    name: str = "edit_file"
    sandbox: Sandbox | None = None
    task: HumanEvalFixTask | None = None

    def call(self, args: dict[str, Any]) -> ToolResult:
        call_id = f"edit_{time.time_ns()}"

        # Second-chance parse: if the adapter's JSON parsing fell back to 'raw',
        # try to parse again here. Handles multi-line contents in tagged args.
        if "raw" in args and "contents" not in args and "body" not in args:
            raw = args["raw"]
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    args = {**args, **parsed}
            except json.JSONDecodeError:
                # Lenient fallback: extract with regex
                import re as _re
                path_m = _re.search(r'"path"\s*:\s*"([^"]+)"', raw)
                cont_m = _re.search(r'"contents"\s*:\s*"(.*)"\s*\}?\s*$', raw, _re.DOTALL)
                if path_m:
                    args["path"] = path_m.group(1)
                if cont_m:
                    # Unescape common escapes
                    args["contents"] = cont_m.group(1).encode().decode("unicode_escape")

        path = args.get("path", "solution.py")
        target = (self.sandbox.path / path) if self.sandbox else Path(path)

        if "contents" in args:
            new_contents = args["contents"]
        elif "body" in args and self.task is not None:
            new_contents = self.task.declaration + args["body"] + "\n"
        else:
            return ToolResult(
                call_id=call_id, ok=False,
                output=f"edit_file requires 'contents' or 'body' arg (got keys: {list(args.keys())})",
                truncated=False, elapsed_seconds=0.01,
            )
        try:
            target.write_text(new_contents)
            return ToolResult(
                call_id=call_id, ok=True,
                output=f"Wrote {len(new_contents)} chars to {path}",
                truncated=False, elapsed_seconds=0.01,
            )
        except Exception as e:
            return ToolResult(
                call_id=call_id, ok=False,
                output=f"Write failed: {e}",
                truncated=False, elapsed_seconds=0.01,
            )


@dataclass
class RunTestsTool:
    name: str = "run_tests"
    sandbox: Sandbox | None = None
    task: HumanEvalFixTask | None = None
    timeout_seconds: int = 20

    def call(self, args: dict[str, Any]) -> ToolResult:
        call_id = f"run_{time.time_ns()}"
        if self.sandbox is None or self.task is None:
            return ToolResult(
                call_id=call_id, ok=False,
                output="RunTestsTool not initialized with sandbox + task",
                truncated=False, elapsed_seconds=0.0,
            )
        # Compose test script: solution.py contents + test harness
        solution = (self.sandbox.path / "solution.py").read_text()
        script = solution + "\n\n" + self.task.test_harness()
        runner_path = self.sandbox.path / "_runner.py"
        runner_path.write_text(script)
        t0 = time.time()
        try:
            result = subprocess.run(
                [sys.executable, str(runner_path)],
                capture_output=True, text=True,
                timeout=self.timeout_seconds,
                cwd=str(self.sandbox.path),
            )
            elapsed = time.time() - t0
            passed = result.returncode == 0 and "TESTS_PASSED" in result.stdout
            # Compact stderr; keep last 1200 chars (last traceback)
            err = (result.stderr or "")[-1200:]
            out = (result.stdout or "")[-400:]
            return ToolResult(
                call_id=call_id, ok=passed,
                output=(
                    f"tests_passed={passed}\n"
                    f"return_code={result.returncode}\n"
                    f"stdout_tail:\n{out}\n"
                    f"stderr_tail:\n{err}"
                ),
                truncated=True, elapsed_seconds=round(elapsed, 3),
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                call_id=call_id, ok=False,
                output=f"Test runner timed out after {self.timeout_seconds}s",
                truncated=False, elapsed_seconds=float(self.timeout_seconds),
            )


# =============================================================================
# Ground-truth oracle (invisible to agent)
# =============================================================================


@dataclass
class HumanEvalFixOracle:
    task: HumanEvalFixTask
    timeout_seconds: int = 20

    def judge(self, task: Task, final_diff: str) -> bool:
        """Apply the agent's final diff (full file) to a fresh sandbox and
        run the test harness. Never uses the agent's sandbox state, so a
        buggy final_diff cannot contaminate prior trajectory runs."""
        del task  # unused
        with tempfile.TemporaryDirectory(prefix="oracle_") as td:
            tmp = Path(td)
            # Heuristic: if the diff looks like a full file, use as-is.
            # Else, prepend the declaration (agent returned just the body).
            if self.task.declaration.split("\n")[0] in final_diff.splitlines()[0:3]:
                file_contents = final_diff
            else:
                file_contents = self.task.declaration + final_diff + "\n"
            (tmp / "solution.py").write_text(file_contents)
            runner = tmp / "_runner.py"
            runner.write_text(file_contents + "\n\n" + self.task.test_harness())
            try:
                result = subprocess.run(
                    [sys.executable, str(runner)],
                    capture_output=True, text=True,
                    timeout=self.timeout_seconds, cwd=str(tmp),
                )
                return result.returncode == 0 and "TESTS_PASSED" in result.stdout
            except subprocess.TimeoutExpired:
                return False
            except Exception:
                return False


# =============================================================================
# Runner — end-to-end on one task
# =============================================================================


def build_agent_system_prompt(task: HumanEvalFixTask) -> str:
    """System prompt for the code-repair agent. Kept tight to fit 7B models'
    attention budget, but includes a worked example because zero-shot format
    compliance is the dominant failure mode at this scale."""
    return (
        "You are a coding agent debugging a Python function.\n"
        "\n"
        "Respond with ONE tagged action per turn. Valid forms:\n"
        "  <tool>read_file</tool><args>{\"path\": \"solution.py\"}</args>\n"
        "  <tool>run_tests</tool><args>{}</args>\n"
        "  <tool>edit_file</tool><args>{\"path\": \"solution.py\", \"contents\": \"<full file>\"}</args>\n"
        "  <final>done</final>\n"
        "\n"
        "REQUIRED PROTOCOL:\n"
        "  Turn 1: read_file to see the buggy code.\n"
        "  Turn 2: run_tests to see the failing tests.\n"
        "  Turn 3+: edit_file with the FULL corrected file (declaration + fixed body).\n"
        "  Next:   run_tests again. If tests PASSED, emit <final>done</final>.\n"
        "          If tests FAILED, edit_file again with a new fix.\n"
        "\n"
        "STRICT RULES:\n"
        f"  * The file is always solution.py. The function is `{task.entry_point}`.\n"
        "  * Call read_file at most ONCE. You already have the contents after that.\n"
        "  * After every edit_file, the very next action MUST be run_tests.\n"
        "  * edit_file 'contents' must be the COMPLETE file including imports.\n"
        "  * NEVER emit <final> before run_tests has returned tests_passed=True.\n"
        "  * No explanation text outside the tags. Emit ONLY a tagged action.\n"
        "\n"
        "EXAMPLE flow (for a different task):\n"
        "  Turn 1: <tool>read_file</tool><args>{\"path\": \"solution.py\"}</args>\n"
        "  Turn 2: <tool>run_tests</tool><args>{}</args>\n"
        "  Turn 3: <tool>edit_file</tool><args>{\"path\": \"solution.py\", \"contents\": \"from typing import List\\n\\ndef foo(x: int) -> int:\\n    return x + 1\\n\"}</args>\n"
        "  Turn 4: <tool>run_tests</tool><args>{}</args>\n"
        "  Turn 5: <final>done</final>\n"
    )


def run_one_task(
    task: HumanEvalFixTask,
    llm_model: str = "qwen2.5-coder:7b",
    verifier_variant: str = "none",  # V0 for smoke test
    seed: int = 0,
    max_turns: int = 15,
    fallback_models: tuple[str, ...] = ("deepseek-r1:latest", "llama2:latest"),
) -> tuple[Trajectory | None, dict[str, Any]]:
    """Run one agent rollout on one HumanEvalFix task end-to-end.

    Returns (trajectory, metadata_dict). Trajectory is None on catastrophic
    failure before the agent loop completes.
    """
    # Sandbox setup
    sandbox = Sandbox(task_id=task.task_id, seed=seed)
    sandbox.setup(task)

    # Harness Card with tighter budget (frugal)
    card = harness_schema.HarnessCard(
        name=f"frugal-humanevalfix-{llm_model}",
        version="0.1",
        base_model=llm_model,
        base_loop="react+self-verify",
        tools=[
            harness_schema.ToolAffordance(
                name="read_file", description="read solution.py",
                schema_hash="sha256:humanevalfix-read-v1",
                timeout_seconds=2, max_output_tokens=4000,
            ),
            harness_schema.ToolAffordance(
                name="edit_file", description="overwrite solution.py",
                schema_hash="sha256:humanevalfix-edit-v1",
                timeout_seconds=2, max_output_tokens=200,
            ),
            harness_schema.ToolAffordance(
                name="run_tests", description="run hidden test harness",
                schema_hash="sha256:humanevalfix-test-v1",
                timeout_seconds=20, max_output_tokens=1500,
            ),
        ],
        context_policy=harness_schema.ContextPolicy(
            max_context_tokens=8192,  # local models
            trimming_strategy="fifo",
            plan_refresh_every_n_turns=5,
        ),
        memory_policy=harness_schema.MemoryPolicy(enabled=False),
        budget=harness_schema.BudgetPolicy(
            max_turns=max_turns, max_cost_usd=0.0,  # local = free
            max_wall_seconds=300,
        ),
        permissions=harness_schema.PermissionPolicy(
            read_scope="repo", write_scope="repo",
            network="none", destructive_op_gating="none",
        ),
        recovery=harness_schema.RecoveryPolicy(
            on_consecutive_failures=3, on_failure_action="plan_refresh",
        ),
        verifier=harness_schema.VerifierSpec(
            enabled=(verifier_variant != "none"),
            model=None if verifier_variant == "none" else "tbd",
            variant=verifier_variant,  # type: ignore[arg-type]
        ),
    )

    # Pick LLM: fall back to available models if preferred one is missing
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
            available = {m["name"] for m in json.loads(r.read().decode()).get("models", [])}
    except Exception:
        available = set()
    chosen = llm_model if llm_model in available else next(
        (m for m in fallback_models if m in available), None
    )
    if chosen is None:
        return None, {"error": "No Ollama models available", "available": list(available)}

    llm = OllamaLLM(
        model=chosen,
        system_prompt=build_agent_system_prompt(task),
        log_path=Path(__file__).resolve().parent / "logs" / f"run_{task.task_id.replace('/', '_')}_seed{seed}.jsonl",
        max_tokens=512,
    )
    verifier = harness_schema.ScriptedVerifier(card.verifier)  # placeholder
    if not card.verifier.enabled:
        verifier = harness_schema.NoneVerifier(card.verifier)

    oracle = HumanEvalFixOracle(task=task)
    tools = {
        "read_file": ReadFileTool(sandbox=sandbox),
        "edit_file": EditFileTool(sandbox=sandbox, task=task),
        "run_tests": RunTestsTool(sandbox=sandbox, task=task),
    }

    cfg = AgentConfig(
        model=chosen, harness_card=card, verifier=verifier,
        tools=tools, task=task.as_schema_task(),
        llm=llm, ground_truth_oracle=oracle,
    )

    t0 = time.time()
    traj = AgentLoop(cfg).run()
    elapsed = time.time() - t0

    # For code tasks, sandbox state at termination IS the submission.
    # Override whatever the agent's parser extracted as final_diff —
    # re-read and re-judge from the authoritative file.
    try:
        current = (sandbox.path / "solution.py").read_text()
        traj.outcome.final_diff = current
        traj.outcome.ground_truth_pass = oracle.judge(
            task.as_schema_task(), current
        )
    except Exception:
        pass

    meta = {
        "chosen_model": chosen,
        "wall_seconds": round(elapsed, 2),
        "turns_used": traj.outcome.turns_used,
        "tokens_in_total": sum(s.tokens_in for s in traj.steps),
        "tokens_out_total": sum(s.tokens_out for s in traj.steps),
        "ground_truth_pass": traj.outcome.ground_truth_pass,
        "sandbox_dir": str(sandbox.path),
    }
    return traj, meta


# =============================================================================
# Smoke test — run against Task Python/0
# =============================================================================


def smoke_test() -> None:
    print("=" * 78)
    print("Frugal runtime smoke test")
    print("=" * 78)

    print("\nLoading HumanEvalFix...")
    tasks = load_humanevalfix(limit=1)
    task = tasks[0]
    print(f"  Task: {task.task_id}")
    print(f"  Entry point: {task.entry_point}")
    print(f"  Buggy solution preview:")
    for line in task.buggy_solution.strip().splitlines()[:6]:
        print(f"    {line}")

    print(f"\nRunning agent loop (max 10 turns)...")
    traj, meta = run_one_task(
        task=task,
        llm_model="qwen2.5-coder:7b",  # will fall back if not pulled yet
        verifier_variant="none",
        seed=0,
        max_turns=10,
    )

    if traj is None:
        print(f"\nCATASTROPHIC FAILURE: {meta}")
        return

    print("\n--- Result ---")
    print(f"  Model used:        {meta['chosen_model']}")
    print(f"  Wall seconds:      {meta['wall_seconds']:.1f}")
    print(f"  Turns used:        {meta['turns_used']}")
    print(f"  Tokens in/out:     {meta['tokens_in_total']} / {meta['tokens_out_total']}")
    print(f"  Ground truth pass: {traj.outcome.ground_truth_pass}  ←")
    print(f"  Final diff (first 400 chars):")
    print("    " + repr(traj.outcome.final_diff[:400]))

    print(f"\n--- Step trace ---")
    for s in traj.steps:
        kind = s.kind.value
        keys = list(s.payload.keys())
        brief = ""
        if kind == "tool_call":
            brief = f"  {s.payload.get('tool')}"
        elif kind == "tool_result":
            brief = f"  ok={s.payload.get('ok')}"
        elif kind == "terminate":
            brief = f"  reason={s.payload.get('reason')}"
        print(f"  [{s.step_index:2d}] {kind:14s} {keys}{brief}")

    print(f"\n  Sandbox retained at: {meta['sandbox_dir']}")
    print("=" * 78)


if __name__ == "__main__":
    # Tight default: just smoke-test one task
    smoke_test()
