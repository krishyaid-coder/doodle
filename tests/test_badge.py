from __future__ import annotations

import json
from pathlib import Path

import pytest

from doodle.badge import (
    DEFAULT_BADGE_LINK,
    SHIELDS_ENDPOINT,
    BadgeReport,
    format_badge,
    grade_from_findings,
)
from doodle.models import Finding, Severity


def _finding(severity: Severity) -> Finding:
    return Finding(
        rule_id="test/rule",
        severity=severity,
        file=Path("/tmp/SKILL.md"),
        line=1,
        column=1,
        message="msg",
    )


# grade_from_findings ─────────────────────────────────────────────────

def test_no_findings_is_a_plus():
    r = grade_from_findings([])
    assert r.grade == "A+"
    assert r.color == "brightgreen"


def test_info_only_is_a():
    r = grade_from_findings([_finding(Severity.INFO)])
    assert r.grade == "A"
    assert r.color == "green"


def test_one_warning_is_b():
    r = grade_from_findings([_finding(Severity.WARNING)])
    assert r.grade == "B"


def test_two_warnings_is_still_b():
    r = grade_from_findings([_finding(Severity.WARNING), _finding(Severity.WARNING)])
    assert r.grade == "B"


def test_three_warnings_is_c():
    r = grade_from_findings([_finding(Severity.WARNING)] * 3)
    assert r.grade == "C"


def test_four_warnings_is_c():
    r = grade_from_findings([_finding(Severity.WARNING)] * 4)
    assert r.grade == "C"


def test_five_warnings_is_d():
    r = grade_from_findings([_finding(Severity.WARNING)] * 5)
    assert r.grade == "D"


def test_any_error_is_f():
    r = grade_from_findings([_finding(Severity.ERROR)])
    assert r.grade == "F"


def test_error_dominates_warnings():
    """One error trumps ten warnings — F is F."""
    findings = [_finding(Severity.ERROR)] + [_finding(Severity.WARNING)] * 10
    r = grade_from_findings(findings)
    assert r.grade == "F"


def test_counts_are_reported():
    findings = [
        _finding(Severity.ERROR),
        _finding(Severity.WARNING),
        _finding(Severity.WARNING),
        _finding(Severity.INFO),
    ]
    r = grade_from_findings(findings)
    assert r.errors == 1
    assert r.warnings == 2
    assert r.infos == 1
    assert r.total == 4


# BadgeReport.url ─────────────────────────────────────────────────────

def test_a_plus_is_url_encoded():
    r = grade_from_findings([])
    assert "A%2B" in r.url
    assert "brightgreen" in r.url
    assert r.url.startswith(SHIELDS_ENDPOINT)


def test_url_includes_style_flat_square():
    r = grade_from_findings([])
    assert "style=flat-square" in r.url


# format_badge ────────────────────────────────────────────────────────

def test_markdown_format_includes_link():
    r = grade_from_findings([])
    out = format_badge(r, fmt="markdown")
    assert out.startswith("[![doodle A+](")
    assert DEFAULT_BADGE_LINK in out


def test_markdown_format_respects_custom_link():
    r = grade_from_findings([])
    out = format_badge(r, fmt="markdown", link="https://example.com/mine")
    assert "https://example.com/mine" in out


def test_url_format_is_just_the_url():
    r = grade_from_findings([])
    out = format_badge(r, fmt="url")
    assert out.startswith(SHIELDS_ENDPOINT)
    assert "\n" not in out.strip()


def test_text_format_is_the_grade():
    r = grade_from_findings([_finding(Severity.WARNING)])
    assert format_badge(r, fmt="text") == "B"


def test_json_format_is_valid_and_has_markdown_field():
    r = grade_from_findings([_finding(Severity.WARNING)])
    parsed = json.loads(format_badge(r, fmt="json"))
    assert parsed["grade"] == "B"
    assert parsed["counts"]["warning"] == 1
    assert parsed["counts"]["error"] == 0
    assert parsed["counts"]["info"] == 0
    assert "markdown" in parsed
    assert parsed["url"].startswith(SHIELDS_ENDPOINT)


def test_unknown_format_raises():
    r = grade_from_findings([])
    with pytest.raises(ValueError, match="unknown badge format"):
        format_badge(r, fmt="xml")
