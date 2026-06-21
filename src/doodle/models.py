from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"error": 2, "warning": 1, "info": 0}[self.value]


class Dialect(str, Enum):
    ANTHROPIC = "anthropic"
    EXTENDED = "extended"


@dataclass
class ParsedSkill:
    """Result of parsing a SKILL.md file."""

    path: Path
    raw_text: str
    raw_lines: list[str]
    frontmatter: dict[str, Any]
    frontmatter_lines: tuple[int, int] | None  # (start, end) 1-indexed, inclusive
    body_start_line: int  # 1-indexed; first line after closing ---
    body_text: str
    body_lines: list[str]
    dialect: Dialect
    parse_errors: list["Finding"] = field(default_factory=list)

    def frontmatter_field_line(self, key: str) -> int:
        """Best-effort line number for a top-level frontmatter key. Returns 0 if not found."""
        if self.frontmatter_lines is None:
            return 0
        start, end = self.frontmatter_lines
        for i in range(start, end + 1):
            line = self.raw_lines[i - 1]
            stripped = line.lstrip()
            if stripped.startswith(f"{key}:") or stripped.startswith(f'"{key}":') or stripped.startswith(f"'{key}':"):
                return i
        return start


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    file: Path
    line: int  # 1-indexed; 0 means file-level
    column: int  # 1-indexed; 0 means line-level
    message: str
    suggestion: str | None = None


@dataclass
class Rule:
    id: str
    title: str
    severity: Severity
    category: str  # description | body | frontmatter | hygiene
    dialects: frozenset[Dialect]
    citation: str | None = None
    fixable: bool = False
    default_enabled: bool = True  # set False for rules that are noisy in practice (opt-in)
