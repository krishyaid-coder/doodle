from __future__ import annotations

import json
from pathlib import Path

from doodle import __version__
from doodle.formatters import format_sarif
from doodle.models import Finding, Severity
from doodle.rules import all_rules


def _sample_finding(tmp_path: Path) -> Finding:
    return Finding(
        rule_id="desc/too-long",
        severity=Severity.WARNING,
        file=tmp_path / "SKILL.md",
        line=3,
        column=1,
        message="Description is 282 characters (max 250).",
        suggestion="Trim to the essential 'what' + concrete trigger phrases.",
    )


def test_sarif_is_valid_json(tmp_path):
    out = format_sarif([_sample_finding(tmp_path)], all_rules(), __version__)
    parsed = json.loads(out)
    assert parsed["version"] == "2.1.0"
    assert parsed["$schema"].startswith("https://")


def test_sarif_run_structure(tmp_path):
    parsed = json.loads(format_sarif([_sample_finding(tmp_path)], all_rules(), __version__))
    assert len(parsed["runs"]) == 1
    run = parsed["runs"][0]
    assert run["tool"]["driver"]["name"] == "doodle"
    assert run["tool"]["driver"]["version"] == __version__
    # All registered rules should appear in the driver.rules list
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert "desc/too-long" in rule_ids
    assert "body/emoji" in rule_ids


def test_sarif_result_has_correct_location(tmp_path):
    finding = _sample_finding(tmp_path)
    parsed = json.loads(format_sarif([finding], all_rules(), __version__))
    results = parsed["runs"][0]["results"]
    assert len(results) == 1
    r = results[0]
    assert r["ruleId"] == "desc/too-long"
    assert r["level"] == "warning"
    region = r["locations"][0]["physicalLocation"]["region"]
    assert region["startLine"] == 3
    assert region["startColumn"] == 1


def test_sarif_severity_mapping(tmp_path):
    findings = [
        Finding("desc/too-long", Severity.ERROR, tmp_path / "a.md", 1, 1, "e"),
        Finding("desc/too-long", Severity.WARNING, tmp_path / "b.md", 1, 1, "w"),
        Finding("desc/too-long", Severity.INFO, tmp_path / "c.md", 1, 1, "i"),
    ]
    parsed = json.loads(format_sarif(findings, all_rules(), __version__))
    levels = [r["level"] for r in parsed["runs"][0]["results"]]
    assert levels == ["error", "warning", "note"]
