"""Tests for the community eval-suite library.

Covers:
- All 10 templates load and produce a passing SKILL.md (integration).
- Each template's descriptions and prompts satisfy shape constraints.
- The embedded prompt lists in ``templates.py`` stay in sync with the
  browsable yaml files under ``eval-suites/`` (drift guard).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from doodle.init import InitOptions, scaffold
from doodle.models import Severity
from doodle.parser import parse_skill
from doodle.rules import run_all
from doodle.templates import TEMPLATES, Template, get_template, list_templates


REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_SUITES_DIR = REPO_ROOT / "eval-suites"


EXPECTED_TEMPLATE_NAMES = {
    "code-reviewer",
    "refactorer",
    "sql-generator",
    "docs-writer",
    "test-writer",
    "security-auditor",
    "debugger",
    "data-engineer",
    "api-designer",
    "skill-creator",
}


def test_all_expected_templates_are_registered():
    assert set(TEMPLATES.keys()) == EXPECTED_TEMPLATE_NAMES


def test_list_templates_returns_stable_order():
    names = [t.name for t in list_templates()]
    assert names == list(TEMPLATES.keys())


def test_get_template_returns_none_for_unknown_name():
    assert get_template("does-not-exist") is None


@pytest.mark.parametrize("template_name", sorted(EXPECTED_TEMPLATE_NAMES))
def test_template_description_fits_lint_constraints(template_name):
    tpl = TEMPLATES[template_name]
    assert 60 <= len(tpl.description) <= 250, (
        f"{template_name} description length {len(tpl.description)} is outside 60-250"
    )
    assert any(phrase in tpl.description.lower() for phrase in ("use when", "trigger with", "when the user")), (
        f"{template_name} description missing a trigger phrase"
    )


@pytest.mark.parametrize("template_name", sorted(EXPECTED_TEMPLATE_NAMES))
def test_template_has_enough_prompts(template_name):
    tpl = TEMPLATES[template_name]
    assert len(tpl.should_fire) >= 8, f"{template_name} needs >= 8 should_fire prompts"
    assert len(tpl.should_not_fire) >= 5, f"{template_name} needs >= 5 should_not_fire prompts"


@pytest.mark.parametrize("template_name", sorted(EXPECTED_TEMPLATE_NAMES))
def test_scaffold_from_template_passes_lint(tmp_path, template_name):
    """Critical: the scaffold each template produces must lint clean."""
    options = InitOptions(
        name="my-skill",
        directory=tmp_path / "my-skill",
        include_eval=True,
        template=template_name,
    )
    created = scaffold(options)
    skill_path = tmp_path / "my-skill" / "SKILL.md"
    eval_path = tmp_path / "my-skill" / "eval.yaml"
    assert skill_path in created
    assert eval_path in created

    skill = parse_skill(skill_path)
    findings = list(run_all(skill))
    non_info = [f for f in findings if f.severity is not Severity.INFO]
    assert non_info == [], (
        f"template {template_name} scaffold produced warnings/errors: "
        f"{[(f.rule_id, f.message) for f in non_info]}"
    )


@pytest.mark.parametrize("template_name", sorted(EXPECTED_TEMPLATE_NAMES))
def test_scaffolded_eval_yaml_is_valid(tmp_path, template_name):
    options = InitOptions(
        name="my-skill",
        directory=tmp_path / "my-skill",
        include_eval=True,
        template=template_name,
    )
    scaffold(options)
    eval_path = tmp_path / "my-skill" / "eval.yaml"
    parsed = yaml.safe_load(eval_path.read_text())
    assert isinstance(parsed, dict)
    assert "should_fire" in parsed
    assert "should_not_fire" in parsed
    assert len(parsed["should_fire"]) == len(TEMPLATES[template_name].should_fire)
    assert len(parsed["should_not_fire"]) == len(TEMPLATES[template_name].should_not_fire)


def test_scaffold_rejects_unknown_template(tmp_path):
    from doodle.init import InitError

    options = InitOptions(
        name="my-skill",
        directory=tmp_path / "my-skill",
        template="not-a-real-template",
    )
    with pytest.raises(InitError, match="Unknown template"):
        scaffold(options)


# ── drift guard: TEMPLATES <-> eval-suites/ ─────────────────────────


@pytest.mark.parametrize("template_name", sorted(EXPECTED_TEMPLATE_NAMES))
def test_embedded_template_matches_on_disk_yaml(template_name):
    """Regression: templates.py and eval-suites/<name>/eval.yaml must not drift.

    If this fails, either the embedded prompts changed without updating the
    yaml, or vice versa. Whichever changed first, update the other.
    """
    yaml_path = EVAL_SUITES_DIR / template_name / "eval.yaml"
    assert yaml_path.is_file(), (
        f"missing eval.yaml on disk for template {template_name!r}: {yaml_path}"
    )
    on_disk = yaml.safe_load(yaml_path.read_text())
    tpl = TEMPLATES[template_name]

    assert list(on_disk.get("should_fire") or []) == list(tpl.should_fire), (
        f"{template_name}: should_fire drift between templates.py and eval-suites/"
    )
    assert list(on_disk.get("should_not_fire") or []) == list(tpl.should_not_fire), (
        f"{template_name}: should_not_fire drift between templates.py and eval-suites/"
    )


def test_eval_suites_directory_has_no_extra_folders():
    """New template folder in eval-suites/ without a matching TEMPLATES entry
    would go undocumented. This test flags that."""
    on_disk = {p.name for p in EVAL_SUITES_DIR.iterdir() if p.is_dir()}
    assert on_disk == EXPECTED_TEMPLATE_NAMES, (
        f"eval-suites/ directories drift from TEMPLATES: "
        f"only-on-disk={on_disk - EXPECTED_TEMPLATE_NAMES}, "
        f"only-in-code={EXPECTED_TEMPLATE_NAMES - on_disk}"
    )
