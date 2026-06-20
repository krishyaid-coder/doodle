from __future__ import annotations

import re
from collections.abc import Iterable

from ..models import Dialect, Finding, ParsedSkill, Rule, Severity


_BOTH = frozenset({Dialect.ANTHROPIC, Dialect.EXTENDED})

MAX_DESC_CHARS = 250
MIN_DESC_CHARS = 60

_TRIGGER_PATTERNS = [
    re.compile(r"\buse\s+when\b", re.IGNORECASE),
    re.compile(r"\btrigger\s+with\b", re.IGNORECASE),
    re.compile(r"\bwhen\s+the\s+user\b", re.IGNORECASE),
    re.compile(r"\binvoke\s+when\b", re.IGNORECASE),
    re.compile(r"\bcall\s+when\b", re.IGNORECASE),
    re.compile(r"\btriggers?:\s*", re.IGNORECASE),
]

# Phrases that overlap default Claude behavior — skills triggering on these tend not to fire,
# because the agent already handles them natively. Curated from anthropics/skills#267 patterns.
_VAGUE_TRIGGER_PHRASES = [
    "reviewing code",
    "reviewing pull requests",
    "writing tests",
    "writing code",
    "writing software",
    "building a feature",
    "building features",
    "debugging code",
    "answering questions",
    "general programming",
    "general coding",
    "coding tasks",
    "any task",
    "any code",
]


def _get_description(skill: ParsedSkill) -> tuple[str | None, int]:
    raw = skill.frontmatter.get("description")
    if raw is None:
        return None, 0
    line = skill.frontmatter_field_line("description")
    return str(raw).strip(), line


def check_too_long(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    desc, line = _get_description(skill)
    if desc is None:
        return
    if len(desc) > MAX_DESC_CHARS:
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=line,
            column=1,
            message=(
                f"Description is {len(desc)} characters (max {MAX_DESC_CHARS}). "
                f"Long descriptions dilute trigger matching and waste context."
            ),
            suggestion="Trim to the essential 'what' + concrete trigger phrases. Move detail into the body.",
        )


def check_too_short(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    desc, line = _get_description(skill)
    if desc is None:
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=skill.frontmatter_lines[0] if skill.frontmatter_lines else 1,
            column=1,
            message="Frontmatter is missing the 'description' field.",
            suggestion="Add a 1-2 sentence description with concrete trigger phrases.",
        )
        return
    if len(desc) < MIN_DESC_CHARS:
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=line,
            column=1,
            message=(
                f"Description is only {len(desc)} characters (min {MIN_DESC_CHARS}). "
                f"Too thin for Claude to match against user intent."
            ),
            suggestion="Add the 'what' and a 'use when…' trigger phrase.",
        )


def check_no_trigger_phrase(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    desc, line = _get_description(skill)
    if not desc:
        return
    if not any(p.search(desc) for p in _TRIGGER_PATTERNS):
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=line,
            column=1,
            message=(
                "Description has no explicit trigger phrase "
                "('Use when…', 'Trigger with…', 'When the user…')."
            ),
            suggestion="Add concrete trigger phrasing so Claude knows when to invoke this skill.",
        )


def check_vague_trigger(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    desc, line = _get_description(skill)
    if not desc:
        return
    lowered = desc.lower()
    hits = [p for p in _VAGUE_TRIGGER_PHRASES if p in lowered]
    if hits:
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=line,
            column=1,
            message=(
                f"Description uses trigger phrase(s) that overlap Claude's default behavior: "
                f"{', '.join(repr(h) for h in hits)}. The skill may never fire."
            ),
            suggestion="Replace with concrete, domain-specific phrases the user is likely to type.",
        )


RULES = [
    Rule(
        id="desc/too-long",
        title="Description exceeds 250 characters",
        severity=Severity.WARNING,
        category="description",
        dialects=_BOTH,
        citation="https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices",
    ),
    Rule(
        id="desc/too-short",
        title="Description is too short or missing",
        severity=Severity.WARNING,
        category="description",
        dialects=_BOTH,
    ),
    Rule(
        id="desc/no-trigger-phrase",
        title="Description has no explicit trigger phrase",
        severity=Severity.WARNING,
        category="description",
        dialects=_BOTH,
        citation="https://github.com/anthropics/skills/issues/267",
    ),
    Rule(
        id="desc/vague-trigger",
        title="Trigger phrase overlaps default Claude behavior",
        severity=Severity.WARNING,
        category="description",
        dialects=_BOTH,
        citation="https://github.com/anthropics/skills/issues/267",
    ),
]

CHECKS = [
    (RULES[0], check_too_long),
    (RULES[1], check_too_short),
    (RULES[2], check_no_trigger_phrase),
    (RULES[3], check_vague_trigger),
]
