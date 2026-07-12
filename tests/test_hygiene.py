"""Tests for the trailing-whitespace and final-newline rules and their fixers.

The desc-blank-lines rule + fixer are already covered by test_rules.py and
test_fixers.py; this module focuses on the two new v0.8 additions.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from doodle.fixers import (
    FIXERS,
    apply_fixes,
    fix_final_newline,
    fix_trailing_whitespace,
)
from doodle.parser import parse_skill
from doodle.rules import run_all
from doodle.rules.hygiene import check_final_newline, check_trailing_whitespace


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_skill(tmp_path):
    def _copy(fixture_subpath: str) -> Path:
        src = FIXTURES / fixture_subpath
        dst = tmp_path / src.parent.name / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        return dst

    return _copy


# ── rule: hygiene/trailing-whitespace ─────────────────────────────────


def test_trailing_whitespace_fires_on_bad_fixture():
    skill = parse_skill(FIXTURES / "trailing-ws" / "SKILL.md")
    from doodle.rules import all_rules

    rule = next(r for r in all_rules() if r.id == "hygiene/trailing-whitespace")
    findings = list(check_trailing_whitespace(skill, rule))
    assert len(findings) >= 2
    assert all(f.rule_id == "hygiene/trailing-whitespace" for f in findings)


def test_trailing_whitespace_stays_silent_on_clean_fixture():
    skill = parse_skill(FIXTURES / "good-skill" / "SKILL.md")
    from doodle.rules import all_rules

    rule = next(r for r in all_rules() if r.id == "hygiene/trailing-whitespace")
    findings = list(check_trailing_whitespace(skill, rule))
    assert findings == [], f"unexpected trailing-whitespace findings: {findings}"


def test_trailing_whitespace_reports_character_count():
    skill = parse_skill(FIXTURES / "trailing-ws" / "SKILL.md")
    from doodle.rules import all_rules

    rule = next(r for r in all_rules() if r.id == "hygiene/trailing-whitespace")
    findings = list(check_trailing_whitespace(skill, rule))
    assert any("3 character" in f.message for f in findings)


# ── rule: hygiene/final-newline ──────────────────────────────────────


def test_final_newline_fires_when_missing():
    skill = parse_skill(FIXTURES / "no-final-newline" / "SKILL.md")
    from doodle.rules import all_rules

    rule = next(r for r in all_rules() if r.id == "hygiene/final-newline")
    findings = list(check_final_newline(skill, rule))
    assert len(findings) == 1
    assert findings[0].rule_id == "hygiene/final-newline"


def test_final_newline_stays_silent_on_clean_fixture():
    skill = parse_skill(FIXTURES / "good-skill" / "SKILL.md")
    from doodle.rules import all_rules

    rule = next(r for r in all_rules() if r.id == "hygiene/final-newline")
    assert list(check_final_newline(skill, rule)) == []


# ── fixers ────────────────────────────────────────────────────────────


def test_fix_trailing_whitespace_strips_all_lines(tmp_skill):
    path = tmp_skill("trailing-ws/SKILL.md")
    skill = parse_skill(path)
    new_text = fix_trailing_whitespace(skill)
    assert new_text is not None
    path.write_text(new_text)
    for line in path.read_text().splitlines():
        assert not line.endswith(" "), f"line has trailing space after fix: {line!r}"
        assert not line.endswith("\t"), f"line has trailing tab after fix: {line!r}"


def test_fix_trailing_whitespace_returns_none_when_clean(tmp_skill):
    path = tmp_skill("good-skill/SKILL.md")
    skill = parse_skill(path)
    assert fix_trailing_whitespace(skill) is None


def test_fix_final_newline_appends_newline(tmp_skill):
    path = tmp_skill("no-final-newline/SKILL.md")
    assert not path.read_text().endswith("\n")
    skill = parse_skill(path)
    new_text = fix_final_newline(skill)
    assert new_text is not None
    path.write_text(new_text)
    assert path.read_text().endswith("\n")


def test_fix_final_newline_returns_none_when_present(tmp_skill):
    path = tmp_skill("good-skill/SKILL.md")
    skill = parse_skill(path)
    assert fix_final_newline(skill) is None


def test_fixers_registered_in_fixer_map():
    assert "hygiene/trailing-whitespace" in FIXERS
    assert "hygiene/final-newline" in FIXERS


def test_apply_fixes_end_to_end_on_trailing_ws(tmp_skill):
    path = tmp_skill("trailing-ws/SKILL.md")
    applied, changed = apply_fixes(
        path, fired_rule_ids={"hygiene/trailing-whitespace"}
    )
    assert "hygiene/trailing-whitespace" in applied
    assert changed
    for line in path.read_text().splitlines():
        assert line == line.rstrip(" \t")


def test_apply_fixes_end_to_end_on_final_newline(tmp_skill):
    path = tmp_skill("no-final-newline/SKILL.md")
    applied, changed = apply_fixes(
        path, fired_rule_ids={"hygiene/final-newline"}
    )
    assert "hygiene/final-newline" in applied
    assert changed
    assert path.read_text().endswith("\n")


# ── run_all wiring ────────────────────────────────────────────────────


def test_run_all_surfaces_new_rules_on_bad_fixture():
    skill = parse_skill(FIXTURES / "trailing-ws" / "SKILL.md")
    findings = list(run_all(skill))
    ids = {f.rule_id for f in findings}
    assert "hygiene/trailing-whitespace" in ids
