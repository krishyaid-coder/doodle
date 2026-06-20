from __future__ import annotations

import re
from collections.abc import Iterable

from ..models import Dialect, Finding, ParsedSkill, Rule, Severity
from ..parser import ANTHROPIC_FIELDS


_BOTH = frozenset({Dialect.ANTHROPIC, Dialect.EXTENDED})
_EXTENDED_ONLY = frozenset({Dialect.EXTENDED})
_ANTHROPIC_ONLY = frozenset({Dialect.ANTHROPIC})

# Body tokens that strongly suggest the skill executes tools.
_TOOL_INVOCATION_PATTERN = re.compile(
    r"\b(Bash|Write|Edit|Read|MultiEdit|NotebookEdit|subprocess\.|os\.system|shell_exec)\b"
)


def check_name_mismatch_dir(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    declared = skill.frontmatter.get("name")
    if declared is None:
        return
    declared = str(declared).strip()
    # The skill's directory name should match `name`. SKILL.md sits inside that directory.
    parent_dir = skill.path.parent.name
    if parent_dir and declared and parent_dir != declared:
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=skill.frontmatter_field_line("name"),
            column=1,
            message=(
                f"Frontmatter name {declared!r} doesn't match parent directory {parent_dir!r}. "
                f"Claude resolves skills by directory; mismatch causes confusion."
            ),
            suggestion=f"Rename the directory to {declared!r} or change the name field to {parent_dir!r}.",
        )


def check_missing_allowed_tools(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    if "allowed-tools" in skill.frontmatter or "allowed_tools" in skill.frontmatter:
        return
    if _TOOL_INVOCATION_PATTERN.search(skill.body_text):
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=skill.frontmatter_lines[0] if skill.frontmatter_lines else 1,
            column=1,
            message=(
                "Body references tools (Bash/Write/Edit/subprocess) but frontmatter omits 'allowed-tools'. "
                "Explicit scoping limits blast radius."
            ),
            suggestion="Add 'allowed-tools: [Read, Write, Bash]' (or the minimal set this skill actually needs).",
        )


def check_unknown_field(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    for key in skill.frontmatter.keys():
        if key not in ANTHROPIC_FIELDS:
            yield Finding(
                rule_id=rule.id,
                severity=rule.severity,
                file=skill.path,
                line=skill.frontmatter_field_line(key),
                column=1,
                message=(
                    f"Frontmatter contains unknown field {key!r} for anthropic dialect. "
                    f"Known fields: {sorted(ANTHROPIC_FIELDS)}."
                ),
                suggestion=f"Remove {key!r}, or switch to the extended dialect if you need it.",
            )


RULES = [
    Rule(
        id="fm/name-mismatch-dir",
        title="Frontmatter name doesn't match parent directory",
        severity=Severity.WARNING,
        category="frontmatter",
        dialects=_BOTH,
    ),
    Rule(
        id="fm/missing-allowed-tools",
        title="Body uses tools but frontmatter omits allowed-tools",
        severity=Severity.WARNING,
        category="frontmatter",
        dialects=_EXTENDED_ONLY,
    ),
    Rule(
        id="fm/unknown-field",
        title="Frontmatter contains unknown field (anthropic dialect)",
        severity=Severity.INFO,
        category="frontmatter",
        dialects=_ANTHROPIC_ONLY,
    ),
]

CHECKS = [
    (RULES[0], check_name_mismatch_dir),
    (RULES[1], check_missing_allowed_tools),
    (RULES[2], check_unknown_field),
]
