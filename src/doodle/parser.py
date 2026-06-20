from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Dialect, Finding, ParsedSkill, Severity


ANTHROPIC_FIELDS = frozenset({"name", "description", "license"})
EXTENDED_HINT_FIELDS = frozenset(
    {
        "version",
        "author",
        "tags",
        "allowed-tools",
        "compatible-with",
        "compatibility",
        "user-invocable",
        "argument-hint",
        "agents",
    }
)


def parse_skill(path: Path) -> ParsedSkill:
    """Parse a SKILL.md file. Always returns a ParsedSkill; parse errors are attached as findings."""
    raw_text = path.read_text(encoding="utf-8")
    raw_lines = raw_text.splitlines()

    fm_data, fm_lines, body_start, parse_errors = _split_frontmatter(path, raw_lines)
    body_lines = raw_lines[body_start - 1 :] if body_start <= len(raw_lines) else []
    body_text = "\n".join(body_lines)

    dialect = detect_dialect(fm_data)

    return ParsedSkill(
        path=path,
        raw_text=raw_text,
        raw_lines=raw_lines,
        frontmatter=fm_data,
        frontmatter_lines=fm_lines,
        body_start_line=body_start,
        body_text=body_text,
        body_lines=body_lines,
        dialect=dialect,
        parse_errors=parse_errors,
    )


def _split_frontmatter(
    path: Path, lines: list[str]
) -> tuple[dict[str, Any], tuple[int, int] | None, int, list[Finding]]:
    """Locate the frontmatter block and parse YAML inside it."""
    errors: list[Finding] = []

    if not lines or lines[0].strip() != "---":
        errors.append(
            Finding(
                rule_id="parse/missing-frontmatter",
                severity=Severity.ERROR,
                file=path,
                line=1,
                column=1,
                message="SKILL.md must start with a YAML frontmatter block delimited by '---'.",
            )
        )
        return {}, None, 1, errors

    close_idx = None
    for i, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            close_idx = i
            break

    if close_idx is None:
        errors.append(
            Finding(
                rule_id="parse/unclosed-frontmatter",
                severity=Severity.ERROR,
                file=path,
                line=1,
                column=1,
                message="Frontmatter opened with '---' but no closing '---' was found.",
            )
        )
        return {}, None, len(lines) + 1, errors

    fm_text = "\n".join(lines[1 : close_idx - 1])
    try:
        loaded = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        errors.append(
            Finding(
                rule_id="parse/invalid-yaml",
                severity=Severity.ERROR,
                file=path,
                line=1,
                column=1,
                message=f"Invalid YAML in frontmatter: {exc}",
            )
        )
        loaded = {}

    if not isinstance(loaded, dict):
        errors.append(
            Finding(
                rule_id="parse/invalid-yaml",
                severity=Severity.ERROR,
                file=path,
                line=1,
                column=1,
                message="Frontmatter must be a YAML mapping.",
            )
        )
        loaded = {}

    return loaded, (1, close_idx), close_idx + 1, errors


def detect_dialect(fm: dict[str, Any]) -> Dialect:
    """Auto-detect dialect by frontmatter shape. Extended dialect wins if any hint field is present."""
    if any(k in fm for k in EXTENDED_HINT_FIELDS):
        return Dialect.EXTENDED
    return Dialect.ANTHROPIC
