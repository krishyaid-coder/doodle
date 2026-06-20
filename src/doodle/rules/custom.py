"""Custom rules loaded from .doodle.toml.

Each ``CustomRuleSpec`` is materialized into a ``(Rule, checker)`` pair so it
plugs into the existing registry alongside built-in rules.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from functools import partial

from ..config import CustomRuleSpec
from ..models import Dialect, Finding, ParsedSkill, Rule, Severity


_BOTH = frozenset({Dialect.ANTHROPIC, Dialect.EXTENDED})


def _check_pattern(spec: CustomRuleSpec, skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    assert spec.pattern is not None
    try:
        pattern = re.compile(spec.pattern)
    except re.error as exc:
        yield Finding(
            rule_id=rule.id,
            severity=Severity.ERROR,
            file=skill.path,
            line=0,
            column=0,
            message=f"Custom rule {rule.id!r} has invalid regex {spec.pattern!r}: {exc}",
        )
        return

    target = spec.applies_to
    if target == "body":
        for offset, content in enumerate(skill.body_lines):
            line_no = skill.body_start_line + offset
            for match in pattern.finditer(content):
                yield Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    file=skill.path,
                    line=line_no,
                    column=match.start() + 1,
                    message=spec.message or f"Pattern {spec.pattern!r} matched.",
                    suggestion=spec.suggestion,
                )
    elif target == "description":
        desc = skill.frontmatter.get("description")
        if isinstance(desc, str):
            for match in pattern.finditer(desc):
                yield Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    file=skill.path,
                    line=skill.frontmatter_field_line("description"),
                    column=match.start() + 1,
                    message=spec.message or f"Pattern {spec.pattern!r} matched in description.",
                    suggestion=spec.suggestion,
                )
    elif target == "name":
        name = skill.frontmatter.get("name")
        if isinstance(name, str) and pattern.search(name):
            yield Finding(
                rule_id=rule.id,
                severity=rule.severity,
                file=skill.path,
                line=skill.frontmatter_field_line("name"),
                column=1,
                message=spec.message or f"Pattern {spec.pattern!r} matched in name.",
                suggestion=spec.suggestion,
            )


def _check_required(spec: CustomRuleSpec, skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    missing = [f for f in spec.fields if f not in skill.frontmatter]
    if not missing:
        return
    yield Finding(
        rule_id=rule.id,
        severity=rule.severity,
        file=skill.path,
        line=skill.frontmatter_lines[0] if skill.frontmatter_lines else 1,
        column=1,
        message=spec.message
        or f"Frontmatter is missing required field(s): {', '.join(repr(m) for m in missing)}.",
        suggestion=spec.suggestion,
    )


CheckerFn = Callable[[ParsedSkill, Rule], Iterable[Finding]]


def build_custom_checks(specs: Iterable[CustomRuleSpec]) -> list[tuple[Rule, CheckerFn]]:
    """Turn declarative specs into (Rule, checker) pairs the registry can run."""
    pairs: list[tuple[Rule, CheckerFn]] = []
    for spec in specs:
        rule = Rule(
            id=spec.id,
            title=spec.message or f"Custom rule {spec.id}",
            severity=spec.severity,
            category="custom",
            dialects=_BOTH,
        )
        if spec.kind == "pattern":
            pairs.append((rule, partial(_check_pattern, spec)))
        elif spec.kind == "frontmatter-required":
            pairs.append((rule, partial(_check_required, spec)))
    return pairs
