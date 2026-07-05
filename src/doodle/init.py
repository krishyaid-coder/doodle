"""doodle init: scaffold a compliant SKILL.md that passes the linter out of the box.

The templates are hand-tuned so that a fresh scaffold produces zero warnings
from ``doodle lint`` under both the anthropic and extended dialects. New
authors go from ``pip install`` to a passing skill in one command; from there
they edit the placeholders inline and rerun the linter as they iterate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


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


_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


ANTHROPIC_TEMPLATE = """\
---
name: {name}
description: A short one-line summary of what this skill does. Use when the user says 'run {name}' or explicitly requests this behavior.
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
description: A short one-line summary of what this skill does. Use when the user says 'run {name}' or explicitly requests this behavior.
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


EVAL_TEMPLATE = """\
model: claude-sonnet-4-5

should_fire:
  - "run {name}"
  - "please invoke {name}"
  - "use the {name} skill"

should_not_fire:
  - "what's the weather"
  - "write a brand-new function from scratch"
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


def scaffold(options: InitOptions) -> list[Path]:
    """Create a SKILL.md and (optionally) an eval.yaml at options.directory.

    Returns the list of files that were written. Raises InitError on any
    validation problem or when overwriting is disallowed.
    """
    validate_name(options.name)
    directory = options.directory
    directory.mkdir(parents=True, exist_ok=True)

    skill_path = directory / "SKILL.md"
    eval_path = directory / "eval.yaml"

    if skill_path.exists() and not options.force:
        raise InitError(f"{skill_path} already exists. Pass --force to overwrite.")
    if options.include_eval and eval_path.exists() and not options.force:
        raise InitError(f"{eval_path} already exists. Pass --force to overwrite.")

    template = ANTHROPIC_TEMPLATE if options.dialect == "anthropic" else EXTENDED_TEMPLATE
    author = options.author or "Your Name <you@example.com>"
    skill_content = template.format(name=options.name, author=author)
    skill_path.write_text(skill_content, encoding="utf-8")

    created = [skill_path]
    if options.include_eval:
        eval_path.write_text(EVAL_TEMPLATE.format(name=options.name), encoding="utf-8")
        created.append(eval_path)

    return created
