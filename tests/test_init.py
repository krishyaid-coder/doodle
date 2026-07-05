from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from doodle.init import InitError, InitOptions, scaffold, validate_name
from doodle.models import Severity
from doodle.parser import parse_skill
from doodle.rules import run_all


# validate_name ────────────────────────────────────────────────────────

def test_validate_name_accepts_kebab_case():
    validate_name("my-skill")
    validate_name("skill123")
    validate_name("a-b-c-d")


def test_validate_name_rejects_camel_case():
    with pytest.raises(InitError):
        validate_name("MySkill")


def test_validate_name_rejects_snake_case():
    with pytest.raises(InitError):
        validate_name("my_skill")


def test_validate_name_rejects_leading_hyphen():
    with pytest.raises(InitError):
        validate_name("-leading")


def test_validate_name_rejects_empty():
    with pytest.raises(InitError):
        validate_name("")


# scaffold: file creation ─────────────────────────────────────────────

def test_scaffold_creates_skill_md(tmp_path):
    options = InitOptions(name="my-skill", directory=tmp_path / "my-skill")
    created = scaffold(options)
    assert created == [tmp_path / "my-skill" / "SKILL.md"]
    assert (tmp_path / "my-skill" / "SKILL.md").exists()


def test_scaffold_creates_missing_parent_directories(tmp_path):
    target = tmp_path / "deeply" / "nested" / "path"
    options = InitOptions(name="foo", directory=target)
    scaffold(options)
    assert (target / "SKILL.md").exists()


def test_scaffold_with_eval_creates_both(tmp_path):
    options = InitOptions(
        name="my-skill",
        directory=tmp_path / "my-skill",
        include_eval=True,
    )
    created = scaffold(options)
    assert len(created) == 2
    assert (tmp_path / "my-skill" / "SKILL.md").exists()
    assert (tmp_path / "my-skill" / "eval.yaml").exists()


def test_scaffold_refuses_existing_skill_md(tmp_path):
    directory = tmp_path / "existing"
    directory.mkdir()
    (directory / "SKILL.md").write_text("pre-existing content")
    options = InitOptions(name="existing", directory=directory)
    with pytest.raises(InitError, match="already exists"):
        scaffold(options)


def test_scaffold_overwrites_with_force(tmp_path):
    directory = tmp_path / "existing"
    directory.mkdir()
    (directory / "SKILL.md").write_text("pre-existing content")
    options = InitOptions(name="existing", directory=directory, force=True)
    scaffold(options)
    content = (directory / "SKILL.md").read_text()
    assert "pre-existing content" not in content
    assert "name: existing" in content


def test_scaffold_refuses_existing_eval_yaml_when_requested(tmp_path):
    directory = tmp_path / "with-eval"
    directory.mkdir()
    (directory / "eval.yaml").write_text("existing eval")
    options = InitOptions(name="with-eval", directory=directory, include_eval=True)
    with pytest.raises(InitError, match="already exists"):
        scaffold(options)


# scaffold: output validation ─────────────────────────────────────────

def test_anthropic_dialect_scaffold_passes_lint(tmp_path):
    """The critical integration test: fresh scaffolds must produce zero warnings."""
    options = InitOptions(name="passing-skill", directory=tmp_path / "passing-skill")
    scaffold(options)
    skill = parse_skill(tmp_path / "passing-skill" / "SKILL.md")
    findings = list(run_all(skill))
    non_info = [f for f in findings if f.severity is not Severity.INFO]
    assert non_info == [], (
        f"Fresh anthropic-dialect scaffold produced warnings/errors: "
        f"{[(f.rule_id, f.message) for f in non_info]}"
    )


def test_extended_dialect_scaffold_passes_lint(tmp_path):
    options = InitOptions(
        name="passing-ext",
        directory=tmp_path / "passing-ext",
        dialect="extended",
    )
    scaffold(options)
    skill = parse_skill(tmp_path / "passing-ext" / "SKILL.md")
    findings = list(run_all(skill))
    non_info = [f for f in findings if f.severity is not Severity.INFO]
    assert non_info == [], (
        f"Fresh extended-dialect scaffold produced warnings/errors: "
        f"{[(f.rule_id, f.message) for f in non_info]}"
    )


def test_scaffolded_eval_yaml_is_valid(tmp_path):
    options = InitOptions(name="my-skill", directory=tmp_path / "my-skill", include_eval=True)
    scaffold(options)
    parsed = yaml.safe_load((tmp_path / "my-skill" / "eval.yaml").read_text())
    assert "should_fire" in parsed
    assert "should_not_fire" in parsed
    assert len(parsed["should_fire"]) >= 3
    assert len(parsed["should_not_fire"]) >= 2


def test_extended_scaffold_includes_author(tmp_path):
    options = InitOptions(
        name="authored",
        directory=tmp_path / "authored",
        dialect="extended",
        author="Krishna Dahale",
    )
    scaffold(options)
    content = (tmp_path / "authored" / "SKILL.md").read_text()
    assert "Krishna Dahale" in content


def test_extended_scaffold_falls_back_to_placeholder_author(tmp_path):
    options = InitOptions(
        name="unauthored",
        directory=tmp_path / "unauthored",
        dialect="extended",
    )
    scaffold(options)
    content = (tmp_path / "unauthored" / "SKILL.md").read_text()
    assert "Your Name" in content
