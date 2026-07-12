"""doodle badge: generate a quality-grade badge for a SKILL.md.

The grade is derived from the same findings that ``doodle lint`` would report,
so a badge is always an honest signal of what a linter run against the file
would produce today.

Grade rubric (calibrated against the 62-skill Quality Report):

    A+   No findings.                           # ~18% of the sampled corpus
    A    Info findings only.                    # style-level nits
    B    1-2 warnings, no errors.
    C    3-4 warnings, no errors.
    D    5+ warnings, no errors.
    F    Any error.                             # skill will misload or misfire

The badge itself is served by shields.io. No hosting on our side, no dynamic
call-back. Authors regenerate the snippet when they update their skill.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote

from .models import Finding, Severity


DEFAULT_BADGE_LINK = "https://github.com/krishyaid-coder/doodle"
SHIELDS_ENDPOINT = "https://img.shields.io/badge"


@dataclass(frozen=True)
class BadgeReport:
    grade: str
    color: str
    errors: int
    warnings: int
    infos: int

    @property
    def total(self) -> int:
        return self.errors + self.warnings + self.infos

    @property
    def url(self) -> str:
        """URL-encoded shields.io badge URL."""
        # "A+" needs URL encoding (+ becomes %2B); shields.io also expects the
        # "?style=flat-square" query string for the modern flat look.
        label = quote(self.grade, safe="")
        return f"{SHIELDS_ENDPOINT}/doodle-{label}-{self.color}?style=flat-square"

    def markdown(self, link: str = DEFAULT_BADGE_LINK) -> str:
        return f"[![doodle {self.grade}]({self.url})]({link})"

    def to_dict(self) -> dict:
        return {
            "grade": self.grade,
            "color": self.color,
            "url": self.url,
            "counts": {
                "error": self.errors,
                "warning": self.warnings,
                "info": self.infos,
                "total": self.total,
            },
        }


def grade_from_findings(findings: list[Finding]) -> BadgeReport:
    """Compute a grade tier from a finding list.

    Rubric matches the module docstring. Kept as a pure function so the CLI,
    tests, and any future badge endpoint use the same rules.
    """
    errors = sum(1 for f in findings if f.severity is Severity.ERROR)
    warnings = sum(1 for f in findings if f.severity is Severity.WARNING)
    infos = sum(1 for f in findings if f.severity is Severity.INFO)

    if errors:
        grade, color = "F", "red"
    elif warnings >= 5:
        grade, color = "D", "orange"
    elif warnings >= 3:
        grade, color = "C", "yellow"
    elif warnings >= 1:
        grade, color = "B", "yellowgreen"
    elif infos:
        grade, color = "A", "green"
    else:
        grade, color = "A+", "brightgreen"

    return BadgeReport(grade=grade, color=color, errors=errors, warnings=warnings, infos=infos)


def format_badge(
    report: BadgeReport,
    fmt: str = "markdown",
    link: str = DEFAULT_BADGE_LINK,
) -> str:
    """Render a BadgeReport in the requested format."""
    fmt = fmt.lower()
    if fmt == "markdown":
        return report.markdown(link=link)
    if fmt == "url":
        return report.url
    if fmt == "text":
        return report.grade
    if fmt == "json":
        return json.dumps({**report.to_dict(), "markdown": report.markdown(link=link)}, indent=2)
    raise ValueError(f"unknown badge format: {fmt!r}")
