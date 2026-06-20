from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from .models import Severity


_VALID_APPLIES_TO = {"body", "description", "name"}
_VALID_KINDS = {"pattern", "frontmatter-required"}
_VALID_SEVERITIES = {"off", "info", "warning", "error"}


@dataclass(frozen=True)
class CustomRuleSpec:
    """A user-declared rule loaded from .doodle.toml."""

    id: str
    kind: str  # "pattern" | "frontmatter-required"
    severity: Severity
    message: str
    suggestion: str | None = None
    # pattern
    pattern: str | None = None
    applies_to: str = "body"  # body | description | name
    # frontmatter-required
    fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathOverride:
    """Per-path disables matched by glob."""

    glob: str
    disabled: tuple[str, ...] = ()


@dataclass
class Config:
    dialect: str = "auto"  # auto | anthropic | extended
    fail_on: str = "warning"  # error | warning | never
    severity_overrides: dict[str, str] = field(default_factory=dict)  # rule_id -> "off"/severity
    custom_rules: tuple[CustomRuleSpec, ...] = ()
    path_overrides: tuple[PathOverride, ...] = ()
    source: Path | None = None
    load_errors: list[str] = field(default_factory=list)


def load_config(explicit: Path | None = None, start: Path | None = None) -> Config:
    """Load doodle config.

    Order of resolution:
        1. ``explicit`` argument (--config flag)
        2. Walk up from ``start`` (or cwd) looking for ``.doodle.toml`` or a
           ``pyproject.toml`` with a ``[tool.doodle]`` table.
        3. Return an empty Config.
    """
    if explicit is not None:
        return _parse(explicit)
    start = start or Path.cwd()
    found = _discover(start)
    if found is not None:
        return _parse(found)
    return Config()


def _discover(start: Path) -> Path | None:
    cur = start.resolve()
    while True:
        candidate = cur / ".doodle.toml"
        if candidate.is_file():
            return candidate
        pyproject = cur / "pyproject.toml"
        if pyproject.is_file():
            try:
                with pyproject.open("rb") as f:
                    data = tomllib.load(f)
                if isinstance(data.get("tool"), dict) and "doodle" in data["tool"]:
                    return pyproject
            except (tomllib.TOMLDecodeError, OSError):
                pass
        if cur.parent == cur:
            return None
        cur = cur.parent


def _parse(path: Path) -> Config:
    errors: list[str] = []
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        return Config(source=path, load_errors=[f"failed to read config {path}: {exc}"])

    if path.name == "pyproject.toml":
        data = data.get("tool", {}).get("doodle", {})

    options = data.get("options", {}) if isinstance(data.get("options"), dict) else {}

    dialect = str(options.get("dialect", "auto")).lower()
    if dialect not in {"auto", "anthropic", "extended"}:
        errors.append(f"options.dialect: invalid value {dialect!r}; using 'auto'")
        dialect = "auto"

    fail_on = str(options.get("fail-on", options.get("fail_on", "warning"))).lower()
    if fail_on not in {"error", "warning", "never"}:
        errors.append(f"options.fail-on: invalid value {fail_on!r}; using 'warning'")
        fail_on = "warning"

    severity_overrides: dict[str, str] = {}
    raw_sev = data.get("severity", {})
    if isinstance(raw_sev, dict):
        for rule_id, value in raw_sev.items():
            v = str(value).lower()
            if v not in _VALID_SEVERITIES:
                errors.append(f"severity[{rule_id!r}]: invalid value {v!r}; ignored")
                continue
            severity_overrides[str(rule_id)] = v

    custom_rules: list[CustomRuleSpec] = []
    for i, raw in enumerate(data.get("rules", []) or []):
        if not isinstance(raw, dict):
            errors.append(f"rules[{i}]: must be a table")
            continue
        spec, err = _parse_custom_rule(raw, i)
        if err:
            errors.append(err)
            continue
        if spec is not None:
            custom_rules.append(spec)

    path_overrides: list[PathOverride] = []
    for i, raw in enumerate(data.get("paths", []) or []):
        if not isinstance(raw, dict):
            errors.append(f"paths[{i}]: must be a table")
            continue
        glob = raw.get("glob")
        if not isinstance(glob, str) or not glob:
            errors.append(f"paths[{i}]: 'glob' is required")
            continue
        disabled = tuple(str(x) for x in (raw.get("disabled") or []))
        path_overrides.append(PathOverride(glob=glob, disabled=disabled))

    return Config(
        dialect=dialect,
        fail_on=fail_on,
        severity_overrides=severity_overrides,
        custom_rules=tuple(custom_rules),
        path_overrides=tuple(path_overrides),
        source=path,
        load_errors=errors,
    )


def _parse_custom_rule(raw: dict[str, Any], index: int) -> tuple[CustomRuleSpec | None, str | None]:
    rule_id = raw.get("id")
    if not isinstance(rule_id, str) or not rule_id:
        return None, f"rules[{index}]: 'id' is required"

    kind = str(raw.get("kind", "pattern")).lower()
    if kind not in _VALID_KINDS:
        return None, f"rules[{index}] ({rule_id}): kind must be one of {sorted(_VALID_KINDS)}"

    sev_raw = str(raw.get("severity", "warning")).lower()
    if sev_raw == "off":
        # 'off' belongs in the [severity] section, not on a rule itself.
        return None, f"rules[{index}] ({rule_id}): severity 'off' is not valid; omit the rule instead"
    if sev_raw not in {"info", "warning", "error"}:
        return None, f"rules[{index}] ({rule_id}): invalid severity {sev_raw!r}"
    severity = Severity(sev_raw)

    message = str(raw.get("message", ""))
    suggestion = raw.get("suggestion")
    suggestion = str(suggestion) if suggestion is not None else None

    if kind == "pattern":
        pattern = raw.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            return None, f"rules[{index}] ({rule_id}): 'pattern' is required for kind=pattern"
        applies_to = str(raw.get("applies-to", raw.get("applies_to", "body"))).lower()
        if applies_to not in _VALID_APPLIES_TO:
            return None, (
                f"rules[{index}] ({rule_id}): applies-to must be one of "
                f"{sorted(_VALID_APPLIES_TO)}"
            )
        return (
            CustomRuleSpec(
                id=rule_id,
                kind=kind,
                severity=severity,
                message=message,
                suggestion=suggestion,
                pattern=pattern,
                applies_to=applies_to,
            ),
            None,
        )

    # frontmatter-required
    fields_raw = raw.get("fields", [])
    if not isinstance(fields_raw, list) or not fields_raw:
        return None, f"rules[{index}] ({rule_id}): 'fields' list is required for kind=frontmatter-required"
    fields = tuple(str(f) for f in fields_raw)
    return (
        CustomRuleSpec(
            id=rule_id,
            kind=kind,
            severity=severity,
            message=message,
            suggestion=suggestion,
            fields=fields,
        ),
        None,
    )
