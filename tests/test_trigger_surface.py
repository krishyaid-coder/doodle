from __future__ import annotations

from pathlib import Path

import pytest

from doodle.models import Severity
from doodle.parser import parse_skill
from doodle.rules import all_rules, run_all
from doodle.templates import TEMPLATES
from doodle.trigger_surface import (
    MIN_CATEGORY_CONFIDENCE,
    MIN_CATEGORY_MATCH,
    analyze,
    best_matching_template,
    coverage,
    load_prompts_for_skill,
    tokenize,
)


FIXTURES = Path(__file__).parent / "fixtures"


# ── tokenize ──────────────────────────────────────────────────────────


def test_tokenize_drops_stopwords():
    # "my" is a stopword; the rest stem to consistent forms
    assert tokenize("review my staged changes") == {"review", "stag", "chang"}


def test_tokenize_is_case_insensitive():
    assert tokenize("Review My Code") == tokenize("review my code")


def test_tokenize_stems_verb_forms_together():
    assert tokenize("reviewing")  == tokenize("review")
    assert tokenize("reviewed") == tokenize("review")


def test_tokenize_collapses_silent_e_verbs():
    """Regression: 'stage' and 'staged' must agree, or a description saying
    'staged diffs' misses a prompt saying 'stage the diff'."""
    assert tokenize("stage") == tokenize("staged") == tokenize("staging")
    assert tokenize("code") == tokenize("coded") == tokenize("coding")


def test_tokenize_does_not_overstem_short_words():
    # "pass" must not become "pas"; "css" must not become "cs"
    assert "pass" in tokenize("security pass")
    assert "css" in tokenize("write css")


def test_tokenize_empty_is_empty():
    assert tokenize("") == set()


# ── coverage ──────────────────────────────────────────────────────────


def test_coverage_full_when_all_words_present():
    assert coverage("reviews code changes carefully", "review code changes") == 1.0


def test_coverage_zero_when_no_overlap():
    assert coverage("performs static analysis", "check my spelling") == 0.0


def test_coverage_partial():
    score = coverage("reviews code", "review my staged code changes")
    assert 0.0 < score < 1.0


def test_coverage_of_stopword_only_prompt_is_one():
    # nothing meaningful to miss
    assert coverage("anything", "the and of") == 1.0


# ── analyze ───────────────────────────────────────────────────────────


def test_analyze_separates_natural_from_abstract_descriptions():
    tpl = TEMPLATES["code-reviewer"]
    natural = (
        "Reviews diffs for correctness and security. Use when the user says "
        "review my changes or wants a check before committing."
    )
    abstract = "Performs heuristic evaluation of committed changesets."

    good = analyze(natural, tpl.should_fire, tpl.should_not_fire, "test")
    bad = analyze(abstract, tpl.should_fire, tpl.should_not_fire, "test")

    assert good.fire_coverage > bad.fire_coverage
    assert good.margin > bad.margin


def test_analyze_reports_missing_words():
    result = analyze("reviews code", ["review my staged diff"], [], "test")
    pc = result.per_prompt[0]
    assert "diff" in pc.missing
    assert "code" not in pc.missing


def test_analyze_marks_expected_fire_correctly():
    result = analyze("x", ["a"], ["b"], "test")
    fire = [p for p in result.per_prompt if p.expected_fire]
    nofire = [p for p in result.per_prompt if not p.expected_fire]
    assert len(fire) == 1 and len(nofire) == 1


def test_margin_is_difference_of_coverages():
    result = analyze("reviews code", ["review code"], ["deploy server"], "test")
    assert result.margin == pytest.approx(
        result.fire_coverage - result.nofire_coverage
    )


def test_weakest_returns_lowest_scoring_fire_prompts_first():
    result = analyze(
        "reviews code",
        ["review code", "audit the kubernetes ingress controller"],
        [],
        "test",
    )
    assert result.weakest[0].score < result.weakest[-1].score


def test_analyze_with_empty_prompt_lists_does_not_crash():
    result = analyze("anything", [], [], "test")
    assert result.fire_coverage == 0.0
    assert result.nofire_coverage == 0.0


# ── category matching ─────────────────────────────────────────────────


def test_best_matching_template_finds_obvious_category():
    desc = (
        "Reviews pull requests and staged diffs, looking for issues before "
        "you commit or merge."
    )
    tpl = best_matching_template(desc)
    assert tpl is not None
    assert tpl.name == "code-reviewer"


def test_best_matching_template_rejects_unrelated_description():
    """A skill in no built-in category must not be assigned to one anyway.

    Regression: before the confidence gate, a brainstorming skill matched
    'data-engineer' at 10% coverage and was then judged against Airflow and
    Kafka prompts.
    """
    desc = (
        "Facilitates open-ended ideation sessions and helps expand on "
        "half-formed thoughts."
    )
    assert best_matching_template(desc) is None


def test_confidence_constants_are_sane():
    assert 0 < MIN_CATEGORY_MATCH < 1
    assert MIN_CATEGORY_CONFIDENCE > 1


# ── prompt resolution ─────────────────────────────────────────────────


def test_load_prompts_prefers_authors_own_eval_yaml():
    skill_path = FIXTURES / "eval-skill" / "SKILL.md"
    skill = parse_skill(skill_path)
    result = load_prompts_for_skill(skill_path, skill.frontmatter["description"])
    assert result is not None
    _, _, source = result
    assert source == "eval.yaml"


def test_load_prompts_falls_back_to_template(tmp_path):
    skill_dir = tmp_path / "reviewer"
    skill_dir.mkdir()
    desc = (
        "Reviews pull requests and staged diffs, looking for issues before "
        "you commit or merge."
    )
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: reviewer\ndescription: {desc}\n---\n\n# Body\n"
    )
    result = load_prompts_for_skill(skill_dir / "SKILL.md", desc)
    assert result is not None
    _, _, source = result
    assert source.startswith("template:")


def test_load_prompts_returns_none_for_uncategorizable_skill(tmp_path):
    skill_dir = tmp_path / "odd"
    skill_dir.mkdir()
    desc = "Facilitates open-ended ideation and expands half-formed thoughts."
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: odd\ndescription: {desc}\n---\n\n# Body\n"
    )
    assert load_prompts_for_skill(skill_dir / "SKILL.md", desc) is None


# ── the rule ──────────────────────────────────────────────────────────


def test_rule_is_registered_at_info_severity():
    rule = next((r for r in all_rules() if r.id == "desc/weak-trigger-surface"), None)
    assert rule is not None
    assert rule.severity is Severity.INFO
    assert rule.category == "description"


def test_rule_stays_silent_when_no_prompt_set(tmp_path):
    skill_dir = tmp_path / "odd"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: odd\n"
        "description: Facilitates open-ended ideation and expands half-formed thoughts.\n"
        "---\n\n# Body\n"
    )
    findings = list(run_all(parse_skill(skill_dir / "SKILL.md")))
    assert not [f for f in findings if f.rule_id == "desc/weak-trigger-surface"]


def test_rule_stays_silent_on_strong_trigger_surface():
    skill = parse_skill(FIXTURES / "eval-skill" / "SKILL.md")
    findings = list(run_all(skill))
    assert not [f for f in findings if f.rule_id == "desc/weak-trigger-surface"]
