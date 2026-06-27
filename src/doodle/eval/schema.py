"""eval.yaml schema + result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


DEFAULT_MODEL = "claude-sonnet-4-5"


@dataclass(frozen=True)
class EvalSuite:
    """A skill's trigger-accuracy test cases.

    Loaded from ``eval.yaml`` sitting next to a SKILL.md.
    """

    should_fire: tuple[str, ...]
    should_not_fire: tuple[str, ...]
    model: str = DEFAULT_MODEL
    skill_name: str | None = None  # inferred from SKILL.md frontmatter if omitted

    @classmethod
    def load(cls, path: Path) -> "EvalSuite":
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: eval file must be a YAML mapping")
        should_fire = tuple(str(p) for p in (data.get("should_fire") or ()))
        should_not_fire = tuple(str(p) for p in (data.get("should_not_fire") or ()))
        if not should_fire and not should_not_fire:
            raise ValueError(
                f"{path}: eval file must define at least one of "
                f"'should_fire' or 'should_not_fire'"
            )
        return cls(
            should_fire=should_fire,
            should_not_fire=should_not_fire,
            model=str(data.get("model", DEFAULT_MODEL)),
            skill_name=data.get("skill_name"),
        )

    def dump(self) -> str:
        """Serialize back to YAML (for ``--generate`` output)."""
        out: dict = {}
        if self.skill_name:
            out["skill_name"] = self.skill_name
        out["model"] = self.model
        out["should_fire"] = list(self.should_fire)
        out["should_not_fire"] = list(self.should_not_fire)
        return yaml.safe_dump(out, sort_keys=False, default_flow_style=False, width=4096)


@dataclass(frozen=True)
class PromptResult:
    prompt: str
    expected_fire: bool
    actually_fired: bool

    @property
    def correct(self) -> bool:
        return self.expected_fire == self.actually_fired


@dataclass
class EvalResult:
    skill_path: Path
    eval_path: Path
    results: list[PromptResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def correct(self) -> int:
        return sum(1 for r in self.results if r.correct)

    @property
    def score(self) -> float:
        return (self.correct / self.total) if self.total else 0.0

    @property
    def misses(self) -> list[PromptResult]:
        """Prompts that should have fired but didn't (false negatives)."""
        return [r for r in self.results if r.expected_fire and not r.actually_fired]

    @property
    def false_positives(self) -> list[PromptResult]:
        """Prompts that shouldn't have fired but did."""
        return [r for r in self.results if not r.expected_fire and r.actually_fired]

    def should_fire_score(self) -> tuple[int, int]:
        items = [r for r in self.results if r.expected_fire]
        return sum(1 for r in items if r.correct), len(items)

    def should_not_fire_score(self) -> tuple[int, int]:
        items = [r for r in self.results if not r.expected_fire]
        return sum(1 for r in items if r.correct), len(items)
