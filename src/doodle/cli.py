from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import Config, load_config
from .formatters import format_json, format_summary, format_text
from .models import Dialect, Severity
from .parser import parse_skill
from .rules import all_rules, run_all
from .rules.custom import build_custom_checks


def _discover(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for p in paths:
        if p.is_dir():
            found.extend(sorted(p.rglob("SKILL.md")))
        elif p.is_file():
            found.append(p)
        else:
            print(f"doodle: path not found: {p}", file=sys.stderr)
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in found:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def _explain(rule_id: str) -> int:
    for rule in all_rules():
        if rule.id == rule_id:
            print(f"{rule.id}  [{rule.severity.value}]  {rule.title}")
            print(f"  category : {rule.category}")
            print(f"  dialects : {', '.join(sorted(d.value for d in rule.dialects))}")
            if rule.citation:
                print(f"  citation : {rule.citation}")
            return 0
    print(f"doodle: unknown rule: {rule_id}", file=sys.stderr)
    print(f"available: {', '.join(sorted(r.id for r in all_rules()))}", file=sys.stderr)
    return 3


def _list_rules() -> int:
    rows = []
    for r in sorted(all_rules(), key=lambda x: (x.category, x.id)):
        dialects = ",".join(sorted(d.value for d in r.dialects))
        rows.append(f"  {r.id:<30}  {r.severity.value:<8}  {dialects:<20}  {r.title}")
    print("\n".join(rows))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="doodle",
        description="A linter for Claude SKILL.md files.",
    )
    parser.add_argument("paths", nargs="*", type=Path, help="SKILL.md files or directories to lint")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--ignore", action="append", default=[], metavar="RULE_ID",
        help="Disable a rule. May be repeated.",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Promote info → warning, warning → error.",
    )
    parser.add_argument(
        "--dialect", choices=["auto", "anthropic", "extended"],
        help="Force a dialect (overrides config).",
    )
    parser.add_argument(
        "--config", type=Path, metavar="PATH",
        help="Path to a .doodle.toml config file.",
    )
    parser.add_argument(
        "--no-config", action="store_true",
        help="Skip auto-discovery of .doodle.toml / pyproject.toml.",
    )
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color in text output.")
    parser.add_argument("--explain", metavar="RULE_ID", help="Print docs for a rule and exit.")
    parser.add_argument("--list-rules", action="store_true", help="List all rules and exit.")
    parser.add_argument("--version", action="version", version=f"doodle {__version__}")

    args = parser.parse_args(argv)

    if args.explain:
        return _explain(args.explain)
    if args.list_rules:
        return _list_rules()

    if not args.paths:
        parser.print_usage(sys.stderr)
        print("doodle: provide one or more SKILL.md paths.", file=sys.stderr)
        return 3

    # Load config (unless suppressed)
    if args.no_config:
        config = Config()
    else:
        config = load_config(explicit=args.config)

    for err in config.load_errors:
        print(f"doodle: config: {err}", file=sys.stderr)

    # Build custom rule pairs once
    custom_pairs = build_custom_checks(config.custom_rules)

    # Resolve forced dialect (CLI > config > auto)
    forced_dialect: Dialect | None = None
    dialect_choice = args.dialect or config.dialect
    if dialect_choice and dialect_choice != "auto":
        forced_dialect = Dialect(dialect_choice)

    files = _discover([p.resolve() for p in args.paths])
    if not files:
        print("doodle: no SKILL.md files found.", file=sys.stderr)
        return 3

    disabled = set(args.ignore)
    # Apply default-disabled rules unless --strict or the user explicitly enabled
    # them via [severity] in config (any value other than "off" counts as opt-in).
    if not args.strict:
        for rule in all_rules():
            if rule.default_enabled:
                continue
            override = config.severity_overrides.get(rule.id)
            if override is None or override == "off":
                disabled.add(rule.id)

    all_findings = []
    for path in files:
        skill = parse_skill(path)
        if forced_dialect is not None:
            skill.dialect = forced_dialect
        all_findings.extend(
            run_all(
                skill,
                disabled=disabled,
                severity_overrides=config.severity_overrides,
                custom_pairs=custom_pairs,
                path_overrides=config.path_overrides,
            )
        )

    if args.strict:
        for f in all_findings:
            if f.severity is Severity.INFO:
                f.severity = Severity.WARNING
            elif f.severity is Severity.WARNING:
                f.severity = Severity.ERROR

    use_color = False if args.no_color else None

    if args.format == "json":
        sys.stdout.write(format_json(all_findings))
    else:
        sys.stdout.write(format_text(all_findings, use_color=use_color))
        sys.stdout.write(format_summary(all_findings, use_color=use_color))

    has_error = any(f.severity is Severity.ERROR for f in all_findings)
    has_warning = any(f.severity is Severity.WARNING for f in all_findings)

    # fail-on policy
    fail_on = config.fail_on
    if fail_on == "never":
        return 0
    if fail_on == "error":
        return 2 if has_error else 0
    # default: 'warning' — any warning or error fails
    if has_error:
        return 2
    if has_warning:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
