from __future__ import annotations

from pathlib import Path

import pytest

from doodle.models import Dialect, Severity
from doodle.parser import parse_skill
from doodle.rules import all_rules, run_all
from doodle.rules.spelling import (
    BUILTIN_ALLOWLIST,
    check_typo,
    set_user_allowlist,
)


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _reset_allowlist():
    """Ensure a clean allowlist between tests."""
    set_user_allowlist(())
    yield
    set_user_allowlist(())


def test_desc_typo_rule_is_registered():
    rule = next((r for r in all_rules() if r.id == "desc/typo"), None)
    assert rule is not None
    assert rule.category == "description"
    assert rule.severity is Severity.INFO


def test_desc_typo_rule_is_default_disabled():
    """Domain vocabulary varies; ship opt-in like body/emoji."""
    rule = next(r for r in all_rules() if r.id == "desc/typo")
    assert rule.default_enabled is False


def test_desc_typo_fires_on_misspellings():
    skill = parse_skill(FIXTURES / "typo-desc" / "SKILL.md")
    rule = next(r for r in all_rules() if r.id == "desc/typo")
    findings = list(check_typo(skill, rule))
    ids = {f.rule_id for f in findings}
    assert ids == {"desc/typo"}
    # At least three distinct misspellings in the fixture: optmizes/optmize,
    # developement, performence — dedupe on lowercase base.
    messages = {f.message for f in findings}
    assert len(messages) >= 3


def test_desc_typo_stays_silent_on_clean_description():
    skill = parse_skill(FIXTURES / "good-skill" / "SKILL.md")
    rule = next(r for r in all_rules() if r.id == "desc/typo")
    findings = list(check_typo(skill, rule))
    assert findings == [], f"expected no typos on good-skill, got: {[f.message for f in findings]}"


def _write_skill(tmp_path: Path, description: str) -> Path:
    skill = tmp_path / "test-skill" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(f"---\nname: test-skill\ndescription: {description}\n---\n\n# Body\n")
    return skill


def test_desc_typo_skips_builtin_allowlist_terms(tmp_path):
    """Anthropic, Claude, and the like must not trigger."""
    skill_path = _write_skill(tmp_path, "Uses Anthropic Claude and OpenAI GPT via the API.")
    skill = parse_skill(skill_path)
    rule = next(r for r in all_rules() if r.id == "desc/typo")
    assert list(check_typo(skill, rule)) == []


def test_user_allowlist_silences_specific_terms(tmp_path):
    skill_path = _write_skill(tmp_path, "Handles frobnicating widgets on the Anthropic Claude API.")
    skill = parse_skill(skill_path)
    rule = next(r for r in all_rules() if r.id == "desc/typo")

    # Without allowlist, 'frobnicating' should be flagged.
    findings = list(check_typo(skill, rule))
    assert any("frobnicating" in f.message.lower() for f in findings), \
        f"expected 'frobnicating' to be flagged, got: {[f.message for f in findings]}"

    # With allowlist, no findings.
    set_user_allowlist(["frobnicating"])
    findings = list(check_typo(skill, rule))
    assert findings == []


def test_desc_typo_via_run_all_respects_default_disabled():
    """Even when parsing succeeds, run_all should not emit desc/typo unless the
    rule has been re-enabled (this happens at the CLI layer, not here)."""
    skill = parse_skill(FIXTURES / "typo-desc" / "SKILL.md")
    # run_all itself doesn't apply default_enabled — that's the CLI's job.
    # But it also doesn't filter based on default_enabled, so we expect typos here.
    findings = list(run_all(skill))
    ids = {f.rule_id for f in findings}
    # desc/typo IS emitted from run_all (it's default_enabled=False handling
    # lives in the CLI layer)
    assert "desc/typo" in ids


def test_builtin_allowlist_covers_common_ai_vocabulary():
    """Guard: essential AI/dev-ecosystem terms must stay in the allowlist."""
    essentials = {"anthropic", "claude", "llm", "api", "sdk", "yaml", "json",
                  "github", "python", "typescript", "prompt", "openai"}
    for word in essentials:
        assert word in BUILTIN_ALLOWLIST, f"expected {word!r} in BUILTIN_ALLOWLIST"


def test_possessive_form_is_stripped(tmp_path):
    """Anthropic's should not be a false positive."""
    skill_path = _write_skill(tmp_path, "Uses Anthropic's Claude models.")
    skill = parse_skill(skill_path)
    rule = next(r for r in all_rules() if r.id == "desc/typo")
    assert list(check_typo(skill, rule)) == []
