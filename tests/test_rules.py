from __future__ import annotations

from pathlib import Path

import pytest

from doodle.models import Dialect, Severity
from doodle.parser import parse_skill
from doodle.rules import run_all


FIXTURES = Path(__file__).parent / "fixtures"


def _findings(name: str) -> list:
    skill = parse_skill(FIXTURES / name / "SKILL.md")
    return list(run_all(skill))


def _ids(findings) -> set[str]:
    return {f.rule_id for f in findings}


def test_good_skill_has_no_findings():
    findings = _findings("good-skill")
    assert findings == [], f"expected clean run, got {[f.rule_id for f in findings]}"


def test_bad_description_fires_all_desc_rules():
    ids = _ids(_findings("bad-description"))
    assert "desc/too-long" in ids
    assert "desc/no-trigger-phrase" in ids
    assert "desc/vague-trigger" in ids


def test_missing_description_fires_too_short():
    ids = _ids(_findings("missing-desc"))
    assert "desc/too-short" in ids


def test_absolute_path_outside_fence_flags():
    findings = _findings("abs-path")
    abs_findings = [f for f in findings if f.rule_id == "body/absolute-user-path"]
    assert len(abs_findings) >= 2  # /Users/alice/... and ~/Downloads/...
    # The line inside the fence should NOT flag.
    flagged_lines = {f.line for f in abs_findings}
    fixture_text = (FIXTURES / "abs-path" / "SKILL.md").read_text().splitlines()
    fenced_line_no = next(i for i, l in enumerate(fixture_text, 1) if "/Users/example/example.txt" in l)
    assert fenced_line_no not in flagged_lines


def test_extended_dialect_detected():
    skill = parse_skill(FIXTURES / "extended-no-tools" / "SKILL.md")
    assert skill.dialect is Dialect.EXTENDED


def test_extended_no_tools_fires_missing_allowed_tools():
    ids = _ids(_findings("extended-no-tools"))
    assert "fm/missing-allowed-tools" in ids


def test_anthropic_dialect_detected_for_good_skill():
    skill = parse_skill(FIXTURES / "good-skill" / "SKILL.md")
    assert skill.dialect is Dialect.ANTHROPIC


def test_severity_ordering():
    assert Severity.ERROR.rank > Severity.WARNING.rank > Severity.INFO.rank


def test_emoji_rule_does_not_fire_by_default():
    """body/emoji is default-disabled (too noisy). It should NOT show up unless opted in."""
    # run_all itself doesn't know about default_enabled — that's the CLI's job.
    # But we verify the metadata: the rule must declare default_enabled=False.
    from doodle.rules import all_rules
    emoji = next(r for r in all_rules() if r.id == "body/emoji")
    assert emoji.default_enabled is False


def test_emoji_rule_fires_when_check_runs():
    """If a caller explicitly runs the check, the rule still works (just default-disabled)."""
    ids = _ids(_findings("has-emoji"))
    # The rule fires from run_all directly (registry has no notion of default_enabled).
    # CLI layer is responsible for adding it to disabled. This test guards the rule logic itself.
    assert "body/emoji" in ids
