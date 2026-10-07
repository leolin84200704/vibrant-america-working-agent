"""The single LLM node's transport: headless Claude Code.

`claude -p` runs under the machine's claude.ai login, so no API key is
involved. The prompt goes in on stdin, the answer comes back as
`structured_output` validated against --json-schema. The process gets a
scrubbed environment (no ANTHROPIC_*; .env points those at another proxy) and
an empty working directory so no project CLAUDE.md or memory index is loaded.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any


class ClaudeError(RuntimeError):
    pass


def _clean_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    env.setdefault("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
    if "/opt/homebrew/bin" not in env["PATH"]:
        env["PATH"] = "/opt/homebrew/bin:" + env["PATH"]
    return env


def ask_json(prompt: str, schema: dict[str, Any], model: str, timeout: int = 900) -> dict[str, Any]:
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
        "--tools", "",
        "--max-turns", "1",
    ]
    with tempfile.TemporaryDirectory(prefix="hl7-triage-llm-") as cwd:
        try:
            proc = subprocess.run(
                cmd, input=prompt, cwd=cwd, env=_clean_env(),
                capture_output=True, text=True, timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise ClaudeError("claude CLI not found on PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise ClaudeError(f"claude -p timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise ClaudeError(f"claude -p exit {proc.returncode}: {proc.stderr.strip()[:500] or proc.stdout.strip()[:500]}")
    try:
        envelope = json.loads(proc.stdout)
    except ValueError as exc:
        raise ClaudeError(f"claude -p returned non-JSON: {proc.stdout[:300]}") from exc
    if envelope.get("is_error"):
        raise ClaudeError(f"claude -p reported an error: {str(envelope.get('result'))[:500]}")
    structured = envelope.get("structured_output")
    if isinstance(structured, dict):
        return structured
    result = envelope.get("result")
    if isinstance(result, str):
        try:
            return json.loads(result)
        except ValueError:
            pass
    raise ClaudeError("claude -p returned no structured_output")
