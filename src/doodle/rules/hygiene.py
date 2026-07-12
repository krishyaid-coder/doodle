from __future__ import annotations

from collections.abc import Iterable

from ..models import Dialect, Finding, ParsedSkill, Rule, Severity


_BOTH = frozenset({Dialect.ANTHROPIC, Dialect.EXTENDED})


def check_desc_blank_lines(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    desc = skill.frontmatter.get("description")
    if not isinstance(desc, str):
        return
    if "\n\n" in desc:
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=skill.frontmatter_field_line("description"),
            column=1,
            message=(
                "Description contains blank line(s) — likely from a YAML folded/block scalar. "
                "Blank lines inside the loaded string may degrade trigger matching."
            ),
            suggestion="Collapse description to a single paragraph with no embedded blank lines.",
        )


def check_trailing_whitespace(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    """Flag lines with trailing whitespace before the newline.

    Trailing whitespace is invisible noise: it inflates diffs, breaks some
    markdown parsers, and signals sloppy tooling. Fixable by simple strip.
    """
    for offset, line in enumerate(skill.raw_lines):
        if not line:
            continue
        stripped = line.rstrip(" \t")
        if stripped != line:
            trailing_len = len(line) - len(stripped)
            yield Finding(
                rule_id=rule.id,
                severity=rule.severity,
                file=skill.path,
                line=offset + 1,
                column=len(stripped) + 1,
                message=(
                    f"Line has {trailing_len} character(s) of trailing whitespace."
                ),
                suggestion="Strip trailing whitespace. Run `doodle --fix` to auto-clean.",
            )


def check_final_newline(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    """Flag files that don't end with a newline.

    Missing trailing newlines cause noisy `git diff` output when the last
    line is edited and irritate POSIX tools that expect files to end with LF.
    """
    if not skill.raw_text:
        return
    if not skill.raw_text.endswith("\n"):
        last_line = max(1, len(skill.raw_lines))
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=last_line,
            column=1,
            message="File does not end with a newline.",
            suggestion="Add a trailing newline. Run `doodle --fix` to auto-add.",
        )


RULES = [
    Rule(
        id="hygiene/desc-blank-lines",
        title="Description contains embedded blank lines",
        severity=Severity.INFO,
        category="hygiene",
        dialects=_BOTH,
        fixable=True,
    ),
    Rule(
        id="hygiene/trailing-whitespace",
        title="Line has trailing whitespace",
        severity=Severity.INFO,
        category="hygiene",
        dialects=_BOTH,
        fixable=True,
    ),
    Rule(
        id="hygiene/final-newline",
        title="File does not end with a newline",
        severity=Severity.INFO,
        category="hygiene",
        dialects=_BOTH,
        fixable=True,
    ),
]

CHECKS = [
    (RULES[0], check_desc_blank_lines),
    (RULES[1], check_trailing_whitespace),
    (RULES[2], check_final_newline),
]
