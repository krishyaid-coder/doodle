from __future__ import annotations

import re
from collections.abc import Iterable

from ..models import Dialect, Finding, ParsedSkill, Rule, Severity


_BOTH = frozenset({Dialect.ANTHROPIC, Dialect.EXTENDED})

BODY_WARN_LINES = 500
BODY_ERROR_LINES = 1500

_ABS_PATH_PATTERN = re.compile(r"(/Users/|/home/|(?<![\w/])~/)")
# Emoji: broad ranges covering pictographs, symbols, dingbats, regional indicators.
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001f300-\U0001f6ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa70-\U0001faff"
    "\U00002600-\U000027bf"
    "\U0001f1e6-\U0001f1ff"
    "]"
)


def _iter_non_fence_lines(body_lines: list[str], body_start_line: int) -> Iterable[tuple[int, str]]:
    """Yield (line_number, content) for body lines outside fenced code blocks."""
    in_fence = False
    fence_marker: str | None = None
    for offset, line in enumerate(body_lines):
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            continue
        if in_fence and stripped.startswith(fence_marker or "```"):
            in_fence = False
            fence_marker = None
            continue
        if in_fence:
            continue
        yield body_start_line + offset, line


def check_too_long(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    n = len(skill.body_lines)
    if BODY_WARN_LINES <= n < BODY_ERROR_LINES:
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=skill.body_start_line,
            column=1,
            message=(
                f"Body is {n} lines (soft cap {BODY_WARN_LINES}). "
                f"Long bodies bloat every agent invocation; prefer progressive disclosure."
            ),
            suggestion="Move detail into separate files referenced from the body, or split into multiple skills.",
        )


def check_way_too_long(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    n = len(skill.body_lines)
    if n >= BODY_ERROR_LINES:
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=skill.body_start_line,
            column=1,
            message=(
                f"Body is {n} lines (hard cap {BODY_ERROR_LINES}). "
                f"At this size the skill is almost certainly a doc dump, not a triggerable instruction set."
            ),
            suggestion="Refactor into multiple skills or extract reference material into separate files.",
        )


def check_absolute_user_path(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    for line_no, content in _iter_non_fence_lines(skill.body_lines, skill.body_start_line):
        for match in _ABS_PATH_PATTERN.finditer(content):
            yield Finding(
                rule_id=rule.id,
                severity=rule.severity,
                file=skill.path,
                line=line_no,
                column=match.start() + 1,
                message=(
                    f"Body contains an absolute user path ({match.group(0)!r}). "
                    f"Skills are installed on other users' machines — hardcoded paths break."
                ),
                suggestion="Use relative paths, environment variables, or document the path as user-provided.",
            )


def check_emoji(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    seen_lines: set[int] = set()
    for line_no, content in _iter_non_fence_lines(skill.body_lines, skill.body_start_line):
        match = _EMOJI_PATTERN.search(content)
        if match and line_no not in seen_lines:
            seen_lines.add(line_no)
            yield Finding(
                rule_id=rule.id,
                severity=rule.severity,
                file=skill.path,
                line=line_no,
                column=match.start() + 1,
                message=f"Body contains emoji ({match.group(0)!r}). Anthropic style guide discourages emoji in skill bodies.",
                suggestion="Replace with text equivalents (e.g. 'Yes'/'No' instead of ✅/❌).",
            )


RULES = [
    Rule(
        id="body/too-long",
        title="Body exceeds 500 lines (soft cap)",
        severity=Severity.WARNING,
        category="body",
        dialects=_BOTH,
        citation="https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices",
    ),
    Rule(
        id="body/way-too-long",
        title="Body exceeds 1500 lines (hard cap)",
        severity=Severity.ERROR,
        category="body",
        dialects=_BOTH,
    ),
    Rule(
        id="body/absolute-user-path",
        title="Body contains an absolute user path",
        severity=Severity.WARNING,
        category="body",
        dialects=_BOTH,
    ),
    Rule(
        id="body/emoji",
        title="Body contains emoji",
        severity=Severity.INFO,
        category="body",
        dialects=_BOTH,
        default_enabled=False,  # 109 hits across 62 sampled skills — too noisy on by default; opt in
    ),
]

CHECKS = [
    (RULES[0], check_too_long),
    (RULES[1], check_way_too_long),
    (RULES[2], check_absolute_user_path),
    (RULES[3], check_emoji),
]
