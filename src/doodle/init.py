"""doodle init: scaffold a compliant SKILL.md that passes the linter out of the box.

The templates are hand-tuned so that a fresh scaffold produces zero warnings
from ``doodle lint`` under both the anthropic and extended dialects. New
authors go from ``pip install`` to a passing skill in one command; from there
they edit the placeholders inline and rerun the linter as they iterate.

Category templates (``--template <name>``) go a step further and pre-fill both
the description and an eval.yaml with prompts appropriate to common skill
categories. See ``src/doodle/templates.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .templates import get_template


class InitError(Exception):
    """Raised when the scaffold cannot be created (bad name, existing files, etc.)."""


@dataclass(frozen=True)
class InitOptions:
    name: str
    directory: Path
    dialect: Literal["anthropic", "extended"] = "anthropic"
    include_eval: bool = False
    force: bool = False
    author: str = ""
    template: str | None = None


_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


GENERIC_DESCRIPTION = (
    "A short one-line summary of what this skill does. Use when the user "
    "says 'run {name}' or explicitly requests this behavior."
)

GENERIC_EVAL_SHOULD_FIRE = (
    'run {name}',
    'please invoke {name}',
    'use the {name} skill',
)

GENERIC_EVAL_SHOULD_NOT_FIRE = (
    "what's the weather",
    'write a brand-new function from scratch',
)


ANTHROPIC_TEMPLATE = """\
---
name: {name}
description: {description}
license: MIT
---

# {name}

Replace this paragraph with a short introduction to what this skill does. This section is what Claude reads to understand your skill's purpose.

## When to invoke

Describe the concrete requests or intents that should trigger this skill. Be specific. Concrete trigger phrases are the single highest-leverage part of the file, per Anthropic issue #267.

- User explicitly asks for {name}
- User is working on a scenario this skill handles

## Behavior

Describe what Claude should do when this skill fires. Cite documentation, list steps, or provide examples. Keep the file under 500 lines. Reference separate files for anything larger.

## Notes

Optional. Anything the model should keep in mind while operating under this skill.
"""


EXTENDED_TEMPLATE = """\
---
name: {name}
description: {description}
version: 0.1.0
author: {author}
tags: []
allowed-tools:
  - Read
---

# {name}

Replace this paragraph with a short introduction to what this skill does.

## When to invoke

Describe the concrete requests or intents that should trigger this skill. Be specific.

- User explicitly asks for {name}
- User is working on a scenario this skill handles

## Behavior

Describe what Claude should do when this skill fires. Keep the file under 500 lines. Reference separate files for anything larger.
"""


def validate_name(name: str) -> None:
    """Ensure the skill name is a kebab-case identifier that matches SKILL.md conventions."""
    if not name:
        raise InitError("Skill name must not be empty.")
    if not _NAME_RE.match(name):
        raise InitError(
            f"Skill name {name!r} must be kebab-case lowercase (letters, digits, hyphens) "
            "and start with a letter or digit."
        )


def _render_eval_yaml(should_fire: tuple[str, ...], should_not_fire: tuple[str, ...]) -> str:
    """Emit a valid eval.yaml with the supplied prompt lists."""
    lines = ["model: claude-sonnet-4-5", "", "should_fire:"]
    for p in should_fire:
        # Double-quote to preserve embedded apostrophes without YAML escapes.
        escaped = p.replace('"', '\\"')
        lines.append(f'  - "{escaped}"')
    lines.append("")
    lines.append("should_not_fire:")
    for p in should_not_fire:
        escaped = p.replace('"', '\\"')
        lines.append(f'  - "{escaped}"')
    lines.append("")
    return "\n".join(lines)


def scaffold(options: InitOptions) -> list[Path]:
    """Create a SKILL.md and (optionally) an eval.yaml at options.directory.

    Returns the list of files that were written. Raises InitError on any
    validation problem, invalid template name, or when overwriting is
    disallowed.
    """
    validate_name(options.name)

    template_spec = None
    if options.template:
        template_spec = get_template(options.template)
        if template_spec is None:
            from .templates import TEMPLATES
            available = ", ".join(sorted(TEMPLATES.keys()))
            raise InitError(
                f"Unknown template {options.template!r}. Available: {available}"
            )

    directory = options.directory
    directory.mkdir(parents=True, exist_ok=True)

    skill_path = directory / "SKILL.md"
    eval_path = directory / "eval.yaml"

    if skill_path.exists() and not options.force:
        raise InitError(f"{skill_path} already exists. Pass --force to overwrite.")
    if options.include_eval and eval_path.exists() and not options.force:
        raise InitError(f"{eval_path} already exists. Pass --force to overwrite.")

    # Description: template-supplied or generic
    if template_spec is not None:
        description = template_spec.description
    else:
        description = GENERIC_DESCRIPTION.format(name=options.name)

    template = ANTHROPIC_TEMPLATE if options.dialect == "anthropic" else EXTENDED_TEMPLATE
    author = options.author or "Your Name <you@example.com>"
    skill_content = template.format(
        name=options.name,
        author=author,
        description=description,
    )
    skill_path.write_text(skill_content, encoding="utf-8")

    created = [skill_path]
    if options.include_eval:
        if template_spec is not None:
            should_fire = template_spec.should_fire
            should_not_fire = template_spec.should_not_fire
        else:
            should_fire = tuple(p.format(name=options.name) for p in GENERIC_EVAL_SHOULD_FIRE)
            should_not_fire = GENERIC_EVAL_SHOULD_NOT_FIRE
        eval_path.write_text(_render_eval_yaml(should_fire, should_not_fire), encoding="utf-8")
        created.append(eval_path)

    return created
