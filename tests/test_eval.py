from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from doodle.eval.generate import (
    build_generation_prompt,
    generate_starter_suite,
    parse_generation_response,
)
from doodle.eval.promptfoo import build_config, parse_results
from doodle.eval.runner import format_eval_result, run_eval
from doodle.eval.schema import DEFAULT_MODEL, EvalResult, EvalSuite, PromptResult


FIXTURES = Path(__file__).parent / "fixtures"
EVAL_DIR = FIXTURES / "eval-skill"


# ── schema ──────────────────────────────────────────────────────────────

def test_eval_suite_loads_from_yaml():
    suite = EvalSuite.load(EVAL_DIR / "eval.yaml")
    assert suite.should_fire == (
        "review my staged changes",
        "security pass before I commit",
        "look this diff over",
    )
    assert suite.should_not_fire == ("write me a new function", "what's the weather")
    assert suite.model == "claude-sonnet-4-5"


def test_eval_suite_requires_at_least_one_prompt(tmp_path):
    bad = tmp_path / "eval.yaml"
    bad.write_text("model: foo\n")
    with pytest.raises(ValueError, match="at least one"):
        EvalSuite.load(bad)


def test_eval_suite_round_trips_via_dump(tmp_path):
    suite = EvalSuite(
        should_fire=("a", "b"),
        should_not_fire=("c",),
        model="m",
        skill_name="test",
    )
    path = tmp_path / "eval.yaml"
    path.write_text(suite.dump())
    reloaded = EvalSuite.load(path)
    assert reloaded.should_fire == suite.should_fire
    assert reloaded.should_not_fire == suite.should_not_fire
    assert reloaded.model == suite.model


def test_eval_result_scoring():
    r = EvalResult(skill_path=Path("/x"), eval_path=Path("/x"))
    r.results = [
        PromptResult("a", True, True),    # correct
        PromptResult("b", True, False),   # miss
        PromptResult("c", False, True),   # false positive
        PromptResult("d", False, False),  # correct
    ]
    assert r.total == 4
    assert r.correct == 2
    assert r.score == 0.5
    assert r.should_fire_score() == (1, 2)
    assert r.should_not_fire_score() == (1, 2)
    assert len(r.misses) == 1
    assert len(r.false_positives) == 1


# ── promptfoo config generation ────────────────────────────────────────

def test_build_config_includes_skill_used_assertion():
    suite = EvalSuite.load(EVAL_DIR / "eval.yaml")
    config = build_config(suite, EVAL_DIR / "SKILL.md", "eval-skill")
    parsed = yaml.safe_load(config.yaml_text)

    assert parsed["providers"][0]["id"] == "anthropic:messages:claude-sonnet-4-5"
    assert parsed["providers"][0]["config"]["skills"][0]["path"].endswith("SKILL.md")
    tests = parsed["tests"]
    # 3 should_fire + 2 should_not_fire
    assert len(tests) == 5
    skill_used = [t for t in tests if t["assert"][0]["type"] == "skill-used"]
    not_skill_used = [t for t in tests if t["assert"][0]["type"] == "not-skill-used"]
    assert len(skill_used) == 3
    assert len(not_skill_used) == 2


def test_build_config_expectations_map_to_prompts():
    suite = EvalSuite.load(EVAL_DIR / "eval.yaml")
    config = build_config(suite, EVAL_DIR / "SKILL.md", "eval-skill")
    fire_prompts = [p for p, fire in config.prompt_expectations if fire]
    no_fire_prompts = [p for p, fire in config.prompt_expectations if not fire]
    assert fire_prompts == list(suite.should_fire)
    assert no_fire_prompts == list(suite.should_not_fire)


# ── parse_results inverts assertion success correctly ──────────────────

def test_parse_results_translates_assertion_success_to_actual_fire():
    expectations = (
        ("p1", True),    # should_fire
        ("p2", True),    # should_fire (but won't)
        ("p3", False),   # should_not_fire (but will)
        ("p4", False),   # should_not_fire
    )
    fake_payload = {
        "results": {
            "results": [
                {"vars": {"prompt": "p1"}, "success": True},   # fired as expected
                {"vars": {"prompt": "p2"}, "success": False},  # didn't fire (miss)
                {"vars": {"prompt": "p3"}, "success": False},  # fired (false positive)
                {"vars": {"prompt": "p4"}, "success": True},   # didn't fire as expected
            ]
        }
    }
    results = parse_results(fake_payload, expectations)
    assert [r.correct for r in results] == [True, False, False, True]
    assert results[0].actually_fired is True
    assert results[1].actually_fired is False
    assert results[2].actually_fired is True
    assert results[3].actually_fired is False


# ── --dry-run path doesn't shell out ───────────────────────────────────

def test_run_eval_dry_run_returns_promptfoo_config():
    out = run_eval(EVAL_DIR / "SKILL.md", dry_run=True)
    assert isinstance(out, str)
    assert "skill-used" in out
    assert "not-skill-used" in out
    parsed = yaml.safe_load(out)
    assert parsed["providers"][0]["config"]["skills"][0]["path"].endswith("SKILL.md")


def test_run_eval_missing_eval_yaml_raises_helpful_error(tmp_path):
    skill = tmp_path / "no-eval"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n")
    with pytest.raises(FileNotFoundError, match="No eval.yaml"):
        run_eval(skill / "SKILL.md", dry_run=True)


# ── format ────────────────────────────────────────────────────────────

def test_format_eval_result_summarizes_score():
    r = EvalResult(skill_path=Path("/x/SKILL.md"), eval_path=Path("/x/eval.yaml"))
    r.results = [
        PromptResult("review my diff", True, True),
        PromptResult("look over this", True, False),
        PromptResult("what's the weather", False, False),
    ]
    text = format_eval_result(r)
    assert "should_fire     1/2" in text
    assert "should_not_fire 1/1" in text
    assert "overall         2/3" in text
    assert "look over this" in text  # miss listed


# ── --generate uses a mocked Anthropic client ──────────────────────────

class _MockMessages:
    def __init__(self, reply_text: str):
        self._reply = reply_text

    def create(self, **kwargs):
        return SimpleNamespace(
            content=[SimpleNamespace(text=self._reply)]
        )


class _MockClient:
    def __init__(self, reply_text: str):
        self.messages = _MockMessages(reply_text)


def test_generate_starter_suite_with_mocked_client():
    reply = """\
Here you go:

{
  "should_fire": ["review my diff", "security pass"],
  "should_not_fire": ["write a function", "what's the weather"]
}
"""
    client = _MockClient(reply)
    suite = generate_starter_suite(EVAL_DIR / "SKILL.md", client=client)
    assert suite.should_fire == ("review my diff", "security pass")
    assert suite.should_not_fire == ("write a function", "what's the weather")
    assert suite.skill_name == "eval-skill"


def test_parse_generation_response_tolerates_extra_prose():
    raw = "Sure thing!\n```json\n{\"should_fire\": [\"a\"], \"should_not_fire\": [\"b\"]}\n```\nDone."
    sf, snf = parse_generation_response(raw)
    assert sf == ["a"]
    assert snf == ["b"]


def test_build_generation_prompt_includes_skill_metadata():
    out = build_generation_prompt("my-skill", "A description that goes in.")
    assert "my-skill" in out
    assert "A description that goes in." in out
    assert "should_fire" in out
    assert "should_not_fire" in out
