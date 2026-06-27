"""High-level orchestration for ``doodle eval`` and ``doodle eval --generate``."""

from __future__ import annotations

import sys
from pathlib import Path

from ..parser import parse_skill
from .promptfoo import build_config, parse_results, run_promptfoo
from .schema import EvalResult, EvalSuite


def _resolve_eval_path(skill_or_eval: Path) -> tuple[Path, Path]:
    """Given either a SKILL.md or an eval.yaml, return (skill_path, eval_path)."""
    p = skill_or_eval
    if p.name == "eval.yaml":
        skill = p.parent / "SKILL.md"
        if not skill.is_file():
            raise FileNotFoundError(f"No SKILL.md next to {p}")
        return skill, p
    if p.name == "SKILL.md":
        ev = p.parent / "eval.yaml"
        if not ev.is_file():
            raise FileNotFoundError(
                f"No eval.yaml next to {p}. Generate one with: "
                f"doodle eval --generate {p}"
            )
        return p, ev
    # Treat as a directory
    if p.is_dir():
        skill = p / "SKILL.md"
        ev = p / "eval.yaml"
        if not skill.is_file() or not ev.is_file():
            raise FileNotFoundError(f"Expected SKILL.md + eval.yaml inside {p}")
        return skill, ev
    raise FileNotFoundError(f"Don't know how to resolve {p} to a skill + eval pair")


def run_eval(skill_or_eval: Path, dry_run: bool = False) -> EvalResult | str:
    """Run the eval suite for a skill. Returns EvalResult, or the generated
    Promptfoo config text if ``dry_run=True``."""
    skill_path, eval_path = _resolve_eval_path(skill_or_eval)
    suite = EvalSuite.load(eval_path)

    skill = parse_skill(skill_path)
    skill_name = suite.skill_name or str(skill.frontmatter.get("name") or skill_path.parent.name)

    config = build_config(suite, skill_path, skill_name)

    if dry_run:
        return config.yaml_text

    # Write config to a temp file Promptfoo will read
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".promptfoo.yaml", delete=False
    ) as f:
        f.write(config.yaml_text)
        config_path = Path(f.name)

    try:
        payload = run_promptfoo(config_path)
    finally:
        config_path.unlink(missing_ok=True)

    results = parse_results(payload, config.prompt_expectations)
    return EvalResult(skill_path=skill_path, eval_path=eval_path, results=results)


def generate_eval(skill_path: Path, model: str | None = None, dry_run: bool = False) -> str | EvalSuite:
    """Generate a starter eval.yaml via Anthropic SDK. Returns the YAML text
    if writing succeeded, or the prompt text if ``dry_run=True``."""
    from .generate import build_generation_prompt, generate_starter_suite

    if dry_run:
        skill = parse_skill(skill_path)
        name = str(skill.frontmatter.get("name") or skill_path.parent.name)
        description = str(skill.frontmatter.get("description") or "")
        return build_generation_prompt(name, description)

    suite = generate_starter_suite(skill_path, model=model or "claude-sonnet-4-5")
    return suite


def format_eval_result(r: EvalResult) -> str:
    sf_correct, sf_total = r.should_fire_score()
    snf_correct, snf_total = r.should_not_fire_score()
    lines = [
        f"\n{r.skill_path}",
        f"  should_fire     {sf_correct}/{sf_total}  ({_pct(sf_correct, sf_total)}%)",
        f"  should_not_fire {snf_correct}/{snf_total}  ({_pct(snf_correct, snf_total)}%)",
        f"  overall         {r.correct}/{r.total}  ({int(round(r.score * 100))}%)",
    ]
    if r.misses:
        lines.append("\n  Misses (expected fire, didn't):")
        for m in r.misses:
            lines.append(f"    - {m.prompt!r}")
    if r.false_positives:
        lines.append("\n  False positives (fired when it shouldn't have):")
        for f in r.false_positives:
            lines.append(f"    - {f.prompt!r}")
    return "\n".join(lines) + "\n"


def _pct(num: int, denom: int) -> int:
    if not denom:
        return 0
    return int(round(100 * num / denom))
