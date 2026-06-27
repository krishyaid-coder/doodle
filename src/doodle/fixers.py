"""Auto-fixers for safe rules.

A fixer is a ``(ParsedSkill) -> str | None`` callable: it returns the new file
contents (full text), or None if no change is needed. Fixers are conservative
by design — anything that requires creative judgment (trimming a description,
rewriting a vague trigger) stays manual.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import yaml

from .models import ParsedSkill
from .parser import parse_skill
from .rules.body import _EMOJI_PATTERN


Fixer = Callable[[ParsedSkill], str | None]


def _serialize_frontmatter(fm: dict) -> str:
    """Dump frontmatter as YAML, preserving insertion order, wide enough to avoid wrapping."""
    return yaml.safe_dump(
        fm,
        sort_keys=False,
        default_flow_style=False,
        width=4096,
        allow_unicode=True,
    ).strip()


def fix_desc_blank_lines(skill: ParsedSkill) -> str | None:
    """Collapse blank lines / runs of whitespace inside the description field."""
    desc = skill.frontmatter.get("description")
    if not isinstance(desc, str) or "\n\n" not in desc:
        return None
    new_desc = re.sub(r"\s+", " ", desc).strip()
    new_fm = dict(skill.frontmatter)
    new_fm["description"] = new_desc
    body_text = "\n".join(skill.body_lines)
    return f"---\n{_serialize_frontmatter(new_fm)}\n---\n{body_text}\n"


def fix_emoji(skill: ParsedSkill) -> str | None:
    """Strip emoji codepoints from the body. Leaves frontmatter untouched."""
    if not _EMOJI_PATTERN.search(skill.body_text):
        return None
    if skill.frontmatter_lines is None:
        return None
    new_body = _EMOJI_PATTERN.sub("", skill.body_text)
    # Clean up doubled spaces left behind by removed emoji
    new_body = re.sub(r" {2,}", " ", new_body)
    _, fm_end = skill.frontmatter_lines
    fm_raw = "\n".join(skill.raw_lines[:fm_end])
    return f"{fm_raw}\n{new_body}\n"


FIXERS: dict[str, Fixer] = {
    "hygiene/desc-blank-lines": fix_desc_blank_lines,
    "body/emoji": fix_emoji,
}


def fixable_rule_ids() -> frozenset[str]:
    return frozenset(FIXERS.keys())


def apply_fixes(path: Path, fired_rule_ids: set[str]) -> tuple[list[str], bool]:
    """Apply all relevant fixers to a file in sequence.

    Re-parses between each fix so line offsets and frontmatter state stay correct.

    Returns:
        (rules_actually_fixed, file_changed)
    """
    applied: list[str] = []
    changed = False
    for rule_id in fired_rule_ids:
        fixer = FIXERS.get(rule_id)
        if fixer is None:
            continue
        skill = parse_skill(path)
        new_text = fixer(skill)
        if new_text is None:
            continue
        if new_text != skill.raw_text:
            path.write_text(new_text, encoding="utf-8")
            applied.append(rule_id)
            changed = True
    return applied, changed
