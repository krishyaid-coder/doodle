from __future__ import annotations

from pathlib import Path

import pytest

from doodle.config import Config, CustomRuleSpec, PathOverride, load_config
from doodle.models import Dialect, Severity
from doodle.parser import parse_skill
from doodle.rules import run_all
from doodle.rules.custom import build_custom_checks


FIXTURES = Path(__file__).parent / "fixtures"
CONFIG_DIR = FIXTURES / "with-config"


def _findings(skill_path: Path, cfg: Config):
    skill = parse_skill(skill_path)
    if cfg.dialect != "auto":
        skill.dialect = Dialect(cfg.dialect)
    pairs = build_custom_checks(cfg.custom_rules)
    return list(
        run_all(
            skill,
            severity_overrides=cfg.severity_overrides,
            custom_pairs=pairs,
            path_overrides=cfg.path_overrides,
        )
    )


def test_load_returns_empty_when_no_config_present(tmp_path):
    cfg = load_config(start=tmp_path)
    assert cfg.source is None
    assert cfg.custom_rules == ()
    assert cfg.severity_overrides == {}


def test_load_explicit_path():
    cfg = load_config(explicit=CONFIG_DIR / ".doodle.toml")
    assert cfg.source is not None
    assert cfg.dialect == "extended"
    assert cfg.severity_overrides == {"body/emoji": "off", "body/too-long": "info"}
    assert len(cfg.custom_rules) == 2
    assert len(cfg.path_overrides) == 1


def test_severity_off_disables_builtin():
    cfg = load_config(explicit=CONFIG_DIR / ".doodle.toml")
    # The fixture skill contains a customer_email token → custom rule fires.
    skill_path = CONFIG_DIR / "skills" / "acme-skill" / "SKILL.md"
    findings = _findings(skill_path, cfg)
    ids = {f.rule_id for f in findings}
    assert "body/emoji" not in ids  # disabled via severity = "off"
    assert "acme/no-customer-pii" in ids  # custom pattern rule fired
    assert "acme/require-team-tag" in ids  # required fields missing


def test_severity_downgrade_applies():
    cfg = load_config(explicit=CONFIG_DIR / ".doodle.toml")
    skill_path = CONFIG_DIR / "skills" / "acme-skill" / "SKILL.md"
    # Synthesize a long body to trip body/too-long
    long_body = "\n".join(["line " + str(i) for i in range(600)])
    target = Path(skill_path.parent / "SKILL.md")
    original = target.read_text()
    target.write_text(original.rstrip() + "\n\n" + long_body)
    try:
        findings = _findings(target, cfg)
        body_long = [f for f in findings if f.rule_id == "body/too-long"]
        assert body_long, "expected body/too-long to fire"
        assert body_long[0].severity is Severity.INFO  # downgraded from warning
    finally:
        target.write_text(original)


def test_custom_pattern_rule_fires():
    cfg = load_config(explicit=CONFIG_DIR / ".doodle.toml")
    skill_path = CONFIG_DIR / "skills" / "acme-skill" / "SKILL.md"
    findings = _findings(skill_path, cfg)
    pii = [f for f in findings if f.rule_id == "acme/no-customer-pii"]
    assert len(pii) == 1
    assert pii[0].severity is Severity.ERROR
    assert "customer_email" in pii[0].message or pii[0].suggestion


def test_custom_required_fields_rule_fires():
    cfg = load_config(explicit=CONFIG_DIR / ".doodle.toml")
    skill_path = CONFIG_DIR / "skills" / "acme-skill" / "SKILL.md"
    findings = _findings(skill_path, cfg)
    req = [f for f in findings if f.rule_id == "acme/require-team-tag"]
    assert len(req) == 1
    assert req[0].severity is Severity.ERROR


def test_invalid_regex_yields_single_error(tmp_path):
    spec = CustomRuleSpec(
        id="acme/broken",
        kind="pattern",
        severity=Severity.WARNING,
        message="broken regex test",
        pattern="(unclosed",
    )
    cfg = Config(custom_rules=(spec,))
    skill_path = CONFIG_DIR / "skills" / "acme-skill" / "SKILL.md"
    findings = _findings(skill_path, cfg)
    broken = [f for f in findings if f.rule_id == "acme/broken"]
    assert len(broken) == 1
    assert broken[0].severity is Severity.ERROR
    assert "invalid regex" in broken[0].message


def test_path_override_disables_rule_for_matching_glob(tmp_path):
    # Build a skill at experiments/foo/SKILL.md that would normally trip desc/vague-trigger
    skill_dir = tmp_path / "experiments" / "foo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: foo\n"
        "description: A skill for reviewing code. Use when the user mentions reviewing pull requests.\n"
        "---\n"
        "# Body\n"
    )
    cfg = Config(
        path_overrides=(PathOverride(glob="**/experiments/**/SKILL.md", disabled=("desc/vague-trigger",)),),
    )
    findings = _findings(skill_dir / "SKILL.md", cfg)
    ids = {f.rule_id for f in findings}
    assert "desc/vague-trigger" not in ids


def test_load_invalid_severity_value_is_reported(tmp_path):
    cfg_path = tmp_path / ".doodle.toml"
    cfg_path.write_text(
        '[severity]\n'
        '"body/emoji" = "loud"\n'
    )
    cfg = load_config(explicit=cfg_path)
    assert any("loud" in err for err in cfg.load_errors)
    assert "body/emoji" not in cfg.severity_overrides


def test_load_rule_missing_id_is_skipped(tmp_path):
    cfg_path = tmp_path / ".doodle.toml"
    cfg_path.write_text(
        '[[rules]]\n'
        'kind = "pattern"\n'
        'pattern = "x"\n'
    )
    cfg = load_config(explicit=cfg_path)
    assert any("'id' is required" in err for err in cfg.load_errors)
    assert cfg.custom_rules == ()


def test_pyproject_section_discovered(tmp_path):
    pp = tmp_path / "pyproject.toml"
    pp.write_text(
        '[tool.doodle.options]\n'
        'dialect = "anthropic"\n'
        '\n'
        '[[tool.doodle.rules]]\n'
        'id = "demo/x"\n'
        'kind = "pattern"\n'
        'pattern = "demo"\n'
        'severity = "warning"\n'
        'message = "demo"\n'
    )
    cfg = load_config(start=tmp_path)
    assert cfg.source == pp
    assert cfg.dialect == "anthropic"
    assert len(cfg.custom_rules) == 1
    assert cfg.custom_rules[0].id == "demo/x"
