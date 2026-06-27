from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from doodle.fixers import (
    FIXERS,
    apply_fixes,
    fix_desc_blank_lines,
    fix_emoji,
    fixable_rule_ids,
)
from doodle.parser import parse_skill


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_skill(tmp_path):
    """Copy a fixture skill into tmp_path so fixers can write in place."""
    def _copy(fixture_subpath: str) -> Path:
        src = FIXTURES / fixture_subpath
        dst = tmp_path / src.parent.name / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        return dst
    return _copy


def test_fixable_rules_match_registry():
    """The FIXERS dict should reflect rules with fixable=True."""
    from doodle.rules import all_rules
    fixable_in_rules = {r.id for r in all_rules() if r.fixable}
    assert fixable_in_rules == fixable_rule_ids()


def test_fix_desc_blank_lines_collapses_whitespace(tmp_skill):
    path = tmp_skill("fix-targets/blank-desc/SKILL.md")
    skill = parse_skill(path)
    assert "\n\n" in skill.frontmatter["description"]  # baseline

    new_text = fix_desc_blank_lines(skill)
    assert new_text is not None
    path.write_text(new_text)

    refreshed = parse_skill(path)
    desc = refreshed.frontmatter["description"]
    assert "\n\n" not in desc
    assert "review my diff" in desc
    assert "security pass" in desc


def test_fix_emoji_strips_codepoints(tmp_skill):
    path = tmp_skill("fix-targets/emoji-body/SKILL.md")
    skill = parse_skill(path)
    assert "✨" in skill.body_text  # baseline

    new_text = fix_emoji(skill)
    assert new_text is not None
    path.write_text(new_text)

    refreshed = parse_skill(path)
    assert "✨" not in refreshed.body_text
    assert "🚀" not in refreshed.body_text
    assert "❌" not in refreshed.body_text
    # frontmatter preserved
    assert refreshed.frontmatter["name"] == "emoji-body"


def test_fix_emoji_returns_none_when_no_emoji(tmp_skill):
    # good-skill fixture has no emoji
    path = tmp_skill("good-skill/SKILL.md")
    skill = parse_skill(path)
    assert fix_emoji(skill) is None


def test_apply_fixes_runs_only_fired_fixable_rules(tmp_skill):
    path = tmp_skill("fix-targets/blank-desc/SKILL.md")
    applied, changed = apply_fixes(path, fired_rule_ids={"hygiene/desc-blank-lines"})
    assert "hygiene/desc-blank-lines" in applied
    assert changed
    # File was modified
    refreshed = parse_skill(path)
    assert "\n\n" not in refreshed.frontmatter["description"]


def test_apply_fixes_skips_rules_not_in_fired_set(tmp_skill):
    path = tmp_skill("fix-targets/emoji-body/SKILL.md")
    # We pass an empty fired set — no fixers should run
    applied, changed = apply_fixes(path, fired_rule_ids=set())
    assert applied == []
    assert not changed
