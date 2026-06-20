from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from fnmatch import fnmatch
from pathlib import PurePath

from ..models import Finding, ParsedSkill, Rule, Severity
from . import body, custom, description, frontmatter, hygiene


_MODULES = [description, body, frontmatter, hygiene]


def all_rules() -> list[Rule]:
    rules: list[Rule] = []
    for mod in _MODULES:
        rules.extend(mod.RULES)
    return rules


def _path_matches(skill_path, glob: str) -> bool:
    """Match using POSIX semantics, trying both relative and absolute forms."""
    posix = PurePath(str(skill_path)).as_posix()
    if fnmatch(posix, glob):
        return True
    # Allow globs that don't include a leading slash to match anywhere
    return fnmatch(posix, f"*/{glob}") or fnmatch(posix, glob.lstrip("/"))


def run_all(
    skill: ParsedSkill,
    disabled: set[str] | None = None,
    severity_overrides: dict[str, str] | None = None,
    custom_pairs: list | None = None,
    path_overrides: Iterable | None = None,
) -> Iterable[Finding]:
    """Run all applicable rules against a parsed skill.

    Parameters
    ----------
    skill:
        The parsed skill file.
    disabled:
        Rule IDs to skip entirely (from --ignore flags).
    severity_overrides:
        Rule-ID -> severity-name overrides from config. ``"off"`` disables.
    custom_pairs:
        ``(Rule, checker)`` pairs produced by :func:`custom.build_custom_checks`.
    path_overrides:
        Iterable of :class:`config.PathOverride` — adds to ``disabled`` if the
        skill's path matches the override's glob.
    """
    disabled = set(disabled or set())
    severity_overrides = severity_overrides or {}
    custom_pairs = list(custom_pairs or [])

    for po in path_overrides or []:
        if _path_matches(skill.path, po.glob):
            disabled.update(po.disabled)

    yield from skill.parse_errors

    all_pairs: list = []
    for mod in _MODULES:
        all_pairs.extend(mod.CHECKS)
    all_pairs.extend(custom_pairs)

    for rule, checker in all_pairs:
        if rule.id in disabled:
            continue

        override = severity_overrides.get(rule.id)
        if override == "off":
            continue
        if override:
            rule = replace(rule, severity=Severity(override))

        if skill.dialect not in rule.dialects:
            continue

        yield from checker(skill, rule)
