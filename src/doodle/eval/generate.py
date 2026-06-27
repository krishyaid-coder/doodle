"""Generate starter eval.yaml via the Anthropic SDK.

Reads a SKILL.md, asks Claude to invent 10 should_fire + 10 should_not_fire
prompts, returns an :class:`EvalSuite`. The user reviews + edits.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..parser import parse_skill
from .schema import EvalSuite, DEFAULT_MODEL


_GENERATE_PROMPT = """\
You are helping author an evaluation suite for a Claude skill.

Skill name: {name}
Skill description:
{description}

Generate exactly 10 user prompts in each of two categories:

1. should_fire — natural-language requests where Claude SHOULD invoke this skill.
   Vary the phrasing (formal/casual, short/long, direct/indirect).

2. should_not_fire — requests that sound thematically adjacent but should NOT
   invoke this skill. Include common confusions a user might phrase.

Return STRICT JSON in exactly this shape, with no commentary:

{{
  "should_fire": ["prompt 1", "prompt 2", ...],
  "should_not_fire": ["prompt 1", "prompt 2", ...]
}}
"""


def build_generation_prompt(name: str, description: str) -> str:
    """Construct the prompt sent to Claude. Exposed for testing / --dry-run."""
    return _GENERATE_PROMPT.format(name=name, description=description.strip())


def parse_generation_response(text: str) -> tuple[list[str], list[str]]:
    """Extract should_fire + should_not_fire from Claude's JSON reply.

    Robust to extra prose around the JSON block.
    """
    # Try to find a JSON object in the response
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    payload = json.loads(match.group(0))
    sf = payload.get("should_fire") or []
    snf = payload.get("should_not_fire") or []
    if not isinstance(sf, list) or not isinstance(snf, list):
        raise ValueError("Expected lists under 'should_fire' and 'should_not_fire'")
    return [str(p) for p in sf], [str(p) for p in snf]


def generate_starter_suite(
    skill_path: Path,
    model: str = DEFAULT_MODEL,
    client=None,
) -> EvalSuite:
    """Use Claude to draft a starter eval.yaml for the given skill.

    Args:
        skill_path: path to a SKILL.md
        model: model name (defaults to claude-sonnet-4-5)
        client: optional Anthropic client (for testing). If None, instantiates
            ``anthropic.Anthropic()`` which reads ANTHROPIC_API_KEY from env.

    Raises:
        ImportError: if the ``anthropic`` package isn't installed.
        RuntimeError: if the API call fails or returns unparseable content.
    """
    if client is None:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for --generate. "
                "Install with: pip install 'doodle-lint[eval]'"
            ) from exc
        client = anthropic.Anthropic()

    skill = parse_skill(skill_path)
    name = str(skill.frontmatter.get("name") or skill_path.parent.name)
    description = str(skill.frontmatter.get("description") or "")
    if not description:
        raise RuntimeError(f"{skill_path} has no description in frontmatter; can't generate.")

    prompt = build_generation_prompt(name, description)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise RuntimeError(f"Anthropic API call failed: {exc}") from exc

    # Extract text from response (handle both SDK content shapes)
    text_blocks = []
    for block in getattr(response, "content", []) or []:
        if hasattr(block, "text"):
            text_blocks.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            text_blocks.append(block.get("text", ""))
    raw_text = "".join(text_blocks)

    sf, snf = parse_generation_response(raw_text)
    return EvalSuite(
        should_fire=tuple(sf),
        should_not_fire=tuple(snf),
        model=model,
        skill_name=name,
    )
