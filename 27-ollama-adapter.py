"""
Ollama adapter — makes a local Ollama model drive the AgentLoop from
04-harness-schema.py.

This is the bridge between "the spec" (AgentLoop in 04-harness-schema.py,
currently demo-stubbed with DeterministicLLM) and "real data" on the 3060.

Design goals:
- Minimal: ~100 lines of adapter, no frameworks.
- Deterministic: seed pinned; temperature=0 by default for reproducibility.
- Logged: every request and response persisted to JSONL for auditability.
- Drop-in: the adapter implements the LLMClient Protocol from 04-harness-schema.py
  so the rest of the agent loop doesn't change.

Run smoke test:  python3 27-ollama-adapter.py
Requires: Ollama daemon running, at least one model pulled (`ollama list`).
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sys

# Import the schema contract from the adjacent file (starts with a digit, so use
# importlib and register in sys.modules so dataclasses can find the module).
import importlib.util
_schema_path = Path(__file__).resolve().parent / "04-harness-schema.py"
_schema_spec = importlib.util.spec_from_file_location("harness_schema", str(_schema_path))
assert _schema_spec and _schema_spec.loader
harness_schema = importlib.util.module_from_spec(_schema_spec)
sys.modules["harness_schema"] = harness_schema  # required for dataclass resolution
_schema_spec.loader.exec_module(harness_schema)

LLMResponse = harness_schema.LLMResponse
ToolCall = harness_schema.ToolCall


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


@dataclass
class OllamaLLM:
    """An LLMClient that talks to a local Ollama daemon."""

    model: str
    temperature: float = 0.0
    max_tokens: int = 1024
    system_prompt: str = ""
    log_path: Path | None = None
    # seed pinning via Ollama's options
    seed: int | None = 20260420
    request_timeout: int = 120
    request_counter: int = field(default=0)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
            return json.loads(resp.read().decode())

    def _log(self, entry: dict[str, Any]) -> None:
        if self.log_path is None:
            return
        with self.log_path.open("a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def sample(self, prompt: str) -> Any:  # LLMResponse
        """Satisfies LLMClient Protocol from 04-harness-schema.py."""
        self.request_counter += 1
        full_prompt = (
            f"{self.system_prompt}\n\n{prompt}" if self.system_prompt else prompt
        )
        t0 = time.time()
        result = self._post({
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "seed": self.seed if self.seed is not None else 0,
            },
        })
        elapsed = time.time() - t0
        raw = result.get("response", "")
        tokens_in = result.get("prompt_eval_count", 0)
        tokens_out = result.get("eval_count", 0)

        action_kind, tool_call, final_diff, plan_text, think = self._parse(raw)

        resp = LLMResponse(
            think=think, action_kind=action_kind,
            tool_call=tool_call, final_diff=final_diff, plan_text=plan_text,
            tokens_in=int(tokens_in), tokens_out=int(tokens_out),
            cost_usd=0.0,  # local — no API cost
        )
        self._log({
            "ts": time.time(), "request_n": self.request_counter,
            "model": self.model, "elapsed_sec": round(elapsed, 3),
            "tokens_in": tokens_in, "tokens_out": tokens_out,
            "prompt_len_chars": len(full_prompt),
            "response_len_chars": len(raw),
            "parsed_action": action_kind,
        })
        return resp

    @staticmethod
    def _parse(raw: str) -> tuple[str, Any, str | None, str | None, str]:
        """Parse the LLM's free-text response into an action.

        Protocol (kept deliberately simple for this frugal setup):
          - If response contains '<plan>...</plan>': plan_refresh action
          - Elif response contains '<tool>NAME</tool>' + '<args>JSON</args>': tool_call
          - Elif response contains '<diff>...</diff>' or '<final>...</final>': terminate
          - Else: treat as think-only (no action); caller may loop or terminate
        """
        think_match = re.search(r"<think>(.*?)</think>", raw, re.DOTALL)
        think = think_match.group(1).strip() if think_match else raw[:400]

        plan_match = re.search(r"<plan>(.*?)</plan>", raw, re.DOTALL)
        if plan_match:
            return "plan_refresh", None, None, plan_match.group(1).strip(), think

        final_match = re.search(r"<(?:diff|final)>(.*?)</(?:diff|final)>", raw, re.DOTALL)
        if final_match:
            return "terminate", None, final_match.group(1).strip(), None, think

        tool_match = re.search(r"<tool>(.*?)</tool>", raw, re.DOTALL)
        args_match = re.search(r"<args>(.*?)</args>", raw, re.DOTALL)
        if tool_match and args_match:
            try:
                args = json.loads(args_match.group(1).strip())
            except json.JSONDecodeError:
                args = {"raw": args_match.group(1).strip()}
            tc = ToolCall(
                tool=tool_match.group(1).strip(),
                arguments=args,
                call_id=f"call_{time.time_ns()}",
            )
            return "tool_call", tc, None, None, think

        # No action parsed — treat as terminate with raw as putative diff
        return "terminate", None, raw.strip()[:2000], None, think


def smoke_test():
    """Verify the adapter against whatever model is available locally."""
    # Prefer a coding model if present, else use whatever Ollama has
    available = []
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as r:
            available = [m["name"] for m in json.loads(r.read().decode()).get("models", [])]
    except Exception as e:
        print(f"ERROR: cannot reach Ollama at {OLLAMA_URL}: {e}")
        return

    if not available:
        print("No Ollama models available. Run `ollama pull qwen2.5-coder:7b`.")
        return

    preference = [
        "qwen2.5-coder:7b", "qwen2.5-coder:7b-instruct",
        "qwen2.5:7b", "deepseek-coder-v2:lite",
        "deepseek-r1:latest", "llama2:latest",
    ]
    chosen = next((m for m in preference if m in available), available[0])
    print(f"Available: {available}")
    print(f"Using:     {chosen}")

    llm = OllamaLLM(
        model=chosen,
        system_prompt=(
            "You are a coding agent. Respond ONLY with one of these tagged forms:\n"
            "  <plan>plan text</plan>\n"
            "  <tool>name</tool><args>{json}</args>\n"
            "  <diff>unified diff text</diff>\n"
            "Keep each response short."
        ),
        log_path=LOG_DIR / f"ollama_smoke_{int(time.time())}.jsonl",
    )
    resp = llm.sample(
        "Task: Write a unified diff that changes `return 0` to `return 1` in src/broken.py.\n"
        "Output a <diff> block with the unified diff."
    )
    print(f"\nParsed action: {resp.action_kind}")
    print(f"Tokens in/out: {resp.tokens_in} / {resp.tokens_out}")
    print(f"Think (trunc): {resp.think[:200]}")
    print(f"Final diff:    {resp.final_diff!r}")
    print(f"\nLog written to: {llm.log_path}")


if __name__ == "__main__":
    smoke_test()
