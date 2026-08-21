"""desc/weak-trigger-surface — the description doesn't use the words users type.

Every other SKILL.md rule (here and in other linters) checks the *form* of a
description: length, voice, presence of the literal phrase "use when". None of
them check whether the description shares vocabulary with how people actually
phrase requests.

That gap matters because skill selection is a matching problem. A description
can be the right length, in the right voice, with an explicit "Use when..."
clause, and still lose every match because it says "committed changesets" where
users say "my code".

Thresholds are calibrated against a 125-skill corpus (see
docs/TRIGGER_SURFACE_REPORT.md). ``fire_coverage < 0.15`` is roughly the bottom
third of published skills.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..models import Dialect, Finding, ParsedSkill, Rule, Severity
from ..trigger_surface import analyze, load_prompts_for_skill


_BOTH = frozenset({Dialect.ANTHROPIC, Dialect.EXTENDED})

# Bottom quartile of the calibration corpus (p25 = 0.198).
WEAK_COVERAGE = 0.20
# Descriptions that match adjacent requests nearly as well as their own.
# p25 of the corpus; below this, discrimination is measurably poor.
POOR_MARGIN = -0.05


def check_weak_trigger_surface(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    desc = skill.frontmatter.get("description")
    if not isinstance(desc, str) or not desc.strip():
        return

    prompts = load_prompts_for_skill(skill.path, desc)
    if prompts is None:
        # No eval.yaml and no category close enough to compare against.
        # Staying silent beats analysing against unrelated prompts.
        return

    should_fire, should_not_fire, source = prompts
    result = analyze(desc, should_fire, should_not_fire, source)

    line = skill.frontmatter_field_line("description")

    if result.fire_coverage < WEAK_COVERAGE:
        missed = result.weakest[:2]
        examples = "; ".join(f"{p.prompt!r}" for p in missed)
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=line,
            column=1,
            message=(
                f"Description shares only {result.fire_coverage:.0%} of its vocabulary "
                f"with realistic user phrasings (compared against {source}). "
                f"Weakest matches: {examples}."
            ),
            suggestion=(
                "Use the words users actually type. Run `doodle surface` on this "
                "file to see which phrasings the description misses."
            ),
        )
    elif result.margin < POOR_MARGIN:
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=line,
            column=1,
            message=(
                f"Description matches requests it should ignore about as well as "
                f"its own ({result.fire_coverage:.0%} vs {result.nofire_coverage:.0%}). "
                f"This predicts over-firing on adjacent requests."
            ),
            suggestion=(
                "Add vocabulary specific to this skill's job, and drop generic "
                "terms shared with neighbouring skills. Run `doodle surface` for detail."
            ),
        )


RULES = [
    Rule(
        id="desc/weak-trigger-surface",
        title="Description doesn't use the vocabulary users type",
        severity=Severity.INFO,
        category="description",
        dialects=_BOTH,
        citation="https://github.com/krishyaid-coder/doodle/blob/main/docs/TRIGGER_SURFACE_REPORT.md",
    ),
]

CHECKS = [
    (RULES[0], check_weak_trigger_surface),
]
