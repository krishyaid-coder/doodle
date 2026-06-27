from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from pathlib import Path

from .models import Finding, Severity


_SEVERITY_LABEL = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "info",
}


def _color(severity: Severity, text: str, use_color: bool) -> str:
    if not use_color:
        return text
    codes = {
        Severity.ERROR: "\x1b[31m",
        Severity.WARNING: "\x1b[33m",
        Severity.INFO: "\x1b[34m",
    }
    return f"{codes[severity]}{text}\x1b[0m"


def format_text(findings: list[Finding], root: Path | None = None, use_color: bool | None = None) -> str:
    if use_color is None:
        use_color = sys.stdout.isatty()
    if not findings:
        return ""

    by_file: dict[Path, list[Finding]] = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)

    lines: list[str] = []
    for path, items in by_file.items():
        display = path.relative_to(root) if root and root in path.parents else path
        lines.append(f"\n{display}")
        for f in items:
            loc = f"{f.line}:{f.column}" if f.line else "-"
            sev = _color(f.severity, _SEVERITY_LABEL[f.severity].ljust(7), use_color)
            lines.append(f"  {loc:<6}  {sev}  {f.message}  {f.rule_id}")
            if f.suggestion:
                lines.append(f"          {f.suggestion}")
    return "\n".join(lines) + "\n"


def format_summary(findings: list[Finding], use_color: bool | None = None) -> str:
    if use_color is None:
        use_color = sys.stdout.isatty()
    errors = sum(1 for f in findings if f.severity is Severity.ERROR)
    warnings = sum(1 for f in findings if f.severity is Severity.WARNING)
    infos = sum(1 for f in findings if f.severity is Severity.INFO)
    if not findings:
        return _color(Severity.INFO, "no issues found", use_color) + "\n"
    parts = []
    if errors:
        parts.append(_color(Severity.ERROR, f"{errors} error{'s' if errors != 1 else ''}", use_color))
    if warnings:
        parts.append(_color(Severity.WARNING, f"{warnings} warning{'s' if warnings != 1 else ''}", use_color))
    if infos:
        parts.append(_color(Severity.INFO, f"{infos} info", use_color))
    return ", ".join(parts) + "\n"


def format_json(findings: Iterable[Finding]) -> str:
    payload = [
        {
            "rule_id": f.rule_id,
            "severity": _SEVERITY_LABEL[f.severity],
            "file": str(f.file),
            "line": f.line,
            "column": f.column,
            "message": f.message,
            "suggestion": f.suggestion,
        }
        for f in findings
    ]
    return json.dumps(payload, indent=2) + "\n"


_SARIF_LEVEL = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
}


def format_sarif(findings: list[Finding], rules: list, version: str) -> str:
    """SARIF 2.1.0 — the format GitHub code scanning consumes.

    Spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
    """
    rule_entries = []
    for rule in rules:
        entry: dict = {
            "id": rule.id,
            "name": rule.id.replace("/", "-"),
            "shortDescription": {"text": rule.title},
            "defaultConfiguration": {"level": _SARIF_LEVEL.get(rule.severity, "warning")},
        }
        if rule.citation:
            entry["helpUri"] = rule.citation
        rule_entries.append(entry)

    results = []
    for f in findings:
        results.append(
            {
                "ruleId": f.rule_id,
                "level": _SARIF_LEVEL.get(f.severity, "warning"),
                "message": {"text": f.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": str(f.file)},
                            "region": {
                                "startLine": max(f.line, 1),
                                "startColumn": max(f.column, 1),
                            },
                        }
                    }
                ],
            }
        )

    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "doodle",
                        "version": version,
                        "informationUri": "https://github.com/krishyaid-coder/doodle",
                        "rules": rule_entries,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(payload, indent=2) + "\n"
