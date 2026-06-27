"""Promptfoo config generator + subprocess runner.

We don't reimplement Promptfoo. We generate its config from our `EvalSuite`,
shell out to ``promptfoo eval --output json``, and parse the results back into
``PromptResult`` instances.

Promptfoo's exact ``skill-used`` assertion schema may evolve; we keep the
config generation in one place so it's easy to update. The user can preview
the generated config with ``--dry-run`` before any subprocess is invoked.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from .schema import EvalSuite, PromptResult


@dataclass(frozen=True)
class PromptfooConfig:
    """Computed Promptfoo config + the prompt→expected_fire mapping we need to score."""

    yaml_text: str
    prompt_expectations: tuple[tuple[str, bool], ...]  # (prompt, expected_fire)


def build_config(suite: EvalSuite, skill_path: Path, skill_name: str) -> PromptfooConfig:
    """Generate a Promptfoo config that runs each prompt with the skill loaded.

    Schema reference: https://www.promptfoo.dev/docs/guides/test-agent-skills/
    """
    tests = []
    expectations: list[tuple[str, bool]] = []

    for prompt in suite.should_fire:
        tests.append(
            {
                "vars": {"prompt": prompt},
                "assert": [{"type": "skill-used", "value": skill_name}],
            }
        )
        expectations.append((prompt, True))

    for prompt in suite.should_not_fire:
        tests.append(
            {
                "vars": {"prompt": prompt},
                "assert": [{"type": "not-skill-used", "value": skill_name}],
            }
        )
        expectations.append((prompt, False))

    config = {
        "description": f"doodle eval — {skill_name}",
        "prompts": ["{{prompt}}"],
        "providers": [
            {
                "id": f"anthropic:messages:{suite.model}",
                "config": {"skills": [{"path": str(skill_path)}]},
            }
        ],
        "tests": tests,
    }
    yaml_text = yaml.safe_dump(config, sort_keys=False, default_flow_style=False, width=4096)
    return PromptfooConfig(yaml_text=yaml_text, prompt_expectations=tuple(expectations))


def promptfoo_available() -> bool:
    """Check whether the ``promptfoo`` binary is on PATH."""
    return shutil.which("promptfoo") is not None


def run_promptfoo(config_path: Path) -> dict:
    """Invoke ``promptfoo eval`` and return parsed JSON results.

    Raises:
        RuntimeError: if promptfoo isn't installed or returns non-zero.
    """
    if not promptfoo_available():
        raise RuntimeError(
            "promptfoo CLI not found in PATH. Install with: "
            "`npm install -g promptfoo` (https://www.promptfoo.dev/docs/installation/)"
        )

    result = subprocess.run(
        ["promptfoo", "eval", "--config", str(config_path), "--output", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 100):  # 100 = some assertions failed (still produces JSON)
        raise RuntimeError(
            f"promptfoo exited {result.returncode}\n"
            f"stderr:\n{result.stderr}\n"
            f"stdout:\n{result.stdout[:500]}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"promptfoo returned non-JSON output: {exc}\n{result.stdout[:500]}")


def parse_results(payload: dict, expectations: tuple[tuple[str, bool], ...]) -> list[PromptResult]:
    """Translate Promptfoo's JSON into our PromptResult list.

    Promptfoo's structure:
        { "results": { "results": [ { "vars": {"prompt": "..."}, "success": bool, ... } ] } }

    We match each test back to its expected_fire via the prompt text.
    """
    raw = payload.get("results", {}).get("results") or payload.get("results") or []
    if not isinstance(raw, list):
        raw = []

    by_prompt: dict[str, bool] = {}
    for row in raw:
        vars_ = row.get("vars") or {}
        prompt = vars_.get("prompt")
        if prompt is None:
            continue
        # success=True means the assertion matched — skill-used or not-skill-used.
        # We invert to derive actually_fired:
        #   should_fire test, success=True  → fired
        #   should_fire test, success=False → didn't fire
        #   should_not_fire test, success=True  → didn't fire
        #   should_not_fire test, success=False → fired
        by_prompt[prompt] = bool(row.get("success"))

    out: list[PromptResult] = []
    for prompt, expected_fire in expectations:
        assertion_passed = by_prompt.get(prompt, False)
        # If the assertion passed, behavior matched expectation
        actually_fired = expected_fire if assertion_passed else (not expected_fire)
        out.append(
            PromptResult(
                prompt=prompt,
                expected_fire=expected_fire,
                actually_fired=actually_fired,
            )
        )
    return out
