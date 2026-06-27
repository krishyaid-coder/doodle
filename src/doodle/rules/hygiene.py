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


RULES = [
    Rule(
        id="hygiene/desc-blank-lines",
        title="Description contains embedded blank lines",
        severity=Severity.INFO,
        category="hygiene",
        dialects=_BOTH,
        fixable=True,
    ),
]

CHECKS = [
    (RULES[0], check_desc_blank_lines),
]
