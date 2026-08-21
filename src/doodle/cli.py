from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import Config, load_config
from .fixers import apply_fixes, fixable_rule_ids
from .formatters import format_json, format_sarif, format_summary, format_text
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
    """Dispatch to the right subcommand. Defaults to `lint` for back-compat."""
    argv = list(sys.argv[1:] if argv is None else argv)
    # Subcommand dispatch: `doodle eval ...`, `doodle init ...`, and
    # `doodle lint ...` are explicit; anything else routes to lint so
    # `doodle <path>` keeps working.
    if argv and argv[0] == "eval":
        return _main_eval(argv[1:])
    if argv and argv[0] == "init":
        return _main_init(argv[1:])
    if argv and argv[0] == "badge":
        return _main_badge(argv[1:])
    if argv and argv[0] == "surface":
        return _main_surface(argv[1:])
    if argv and argv[0] == "lint":
        argv = argv[1:]
    return _main_lint(argv)


def _main_surface(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="doodle surface",
        description=(
            "Analyse how well a skill's description matches the words users "
            "actually type. Compares the description against realistic prompts "
            "from the skill's own eval.yaml, or the closest built-in category."
        ),
    )
    parser.add_argument("path", type=Path, help="Path to a SKILL.md file.")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show every prompt, not just the weakest matches.",
    )
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"doodle surface: file not found: {args.path}", file=sys.stderr)
        return 3

    from .trigger_surface import analyze, load_prompts_for_skill

    skill = parse_skill(args.path)
    desc = skill.frontmatter.get("description")
    if not isinstance(desc, str) or not desc.strip():
        print(f"doodle surface: {args.path} has no description to analyse.", file=sys.stderr)
        return 3

    prompts = load_prompts_for_skill(args.path, desc)
    if prompts is None:
        print(
            "doodle surface: no prompt set available for this skill.\n"
            "  Add an eval.yaml next to SKILL.md, or scaffold one with:\n"
            f"    doodle init {skill.frontmatter.get('name', 'my-skill')} --template=<category> --eval",
            file=sys.stderr,
        )
        return 3

    should_fire, should_not_fire, source = prompts
    result = analyze(desc, should_fire, should_not_fire, source)

    if args.format == "json":
        import json

        payload = {
            "file": str(args.path),
            "source": result.source,
            "fire_coverage": round(result.fire_coverage, 4),
            "nofire_coverage": round(result.nofire_coverage, 4),
            "margin": round(result.margin, 4),
            "prompts": [
                {
                    "prompt": p.prompt,
                    "expected_fire": p.expected_fire,
                    "coverage": round(p.score, 4),
                    "missing": list(p.missing),
                }
                for p in result.per_prompt
            ],
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 0

    use_color = sys.stdout.isatty()

    def dim(s: str) -> str:
        return f"\x1b[2m{s}\x1b[0m" if use_color else s

    def bold(s: str) -> str:
        return f"\x1b[1m{s}\x1b[0m" if use_color else s

    print(f"\n{args.path}")
    print(dim(f"  prompts from: {result.source}"))
    print()
    print(f"  {bold('coverage of should-fire prompts')}   {result.fire_coverage:.0%}")
    print(f"  {bold('coverage of should-not-fire')}       {result.nofire_coverage:.0%}")
    print(f"  {bold('margin')}                            {result.margin:+.0%}")
    print()

    shown = [p for p in result.per_prompt if p.expected_fire]
    if not args.all:
        shown = list(result.weakest)
        print(dim("  weakest should-fire matches (pass --all to see every prompt):"))
    else:
        print(dim("  should-fire prompts:"))
    for p in shown:
        print(f"    {p.score:>4.0%}  {p.prompt}")
        if p.missing:
            preview = ", ".join(p.missing[:6])
            print(dim(f"          missing: {preview}"))

    if args.all:
        print()
        print(dim("  should-not-fire prompts (lower is better):"))
        for p in result.per_prompt:
            if p.expected_fire:
                continue
            print(f"    {p.score:>4.0%}  {p.prompt}")

    print()
    if result.fire_coverage < 0.15:
        print("  Weak trigger surface. The description likely underfires on natural phrasings.")
    elif result.margin < -0.05:
        print("  Poor discrimination. The description may fire on requests it should ignore.")
    else:
        print("  Trigger surface looks reasonable.")
    print()
    return 0


def _main_badge(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="doodle badge",
        description=(
            "Generate a quality-grade badge for a SKILL.md, backed by "
            "shields.io. Grade reflects the same findings 'doodle lint' would "
            "report today: A+ (clean), A (info only), B/C/D (progressive warnings), "
            "F (any error)."
        ),
    )
    parser.add_argument("path", type=Path, help="Path to a single SKILL.md file.")
    parser.add_argument(
        "--format",
        choices=["markdown", "url", "text", "json"],
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--link",
        default=None,
        help="Override the badge's target URL (default: doodle repo).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a .doodle.toml config file (badge respects your overrides).",
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help="Skip auto-discovery of .doodle.toml.",
    )
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"doodle badge: file not found: {args.path}", file=sys.stderr)
        return 3
    if args.path.name != "SKILL.md":
        print(
            f"doodle badge: expected a SKILL.md file, got: {args.path.name}",
            file=sys.stderr,
        )
        return 3

    # Load config so severity overrides + user allowlists + custom rules apply
    if args.no_config:
        config = Config()
    else:
        config = load_config(explicit=args.config)

    # Push user allowlist into spelling rule module
    from .rules.spelling import set_user_allowlist
    set_user_allowlist(config.spelling_allowlist)

    custom_pairs = build_custom_checks(config.custom_rules)

    # Compute effective disabled set (same logic as _main_lint but simpler:
    # no --ignore, no --strict override at the badge layer)
    disabled: set[str] = set()
    for rule in all_rules():
        if rule.default_enabled:
            continue
        override = config.severity_overrides.get(rule.id)
        if override is None or override == "off":
            disabled.add(rule.id)

    forced_dialect: Dialect | None = None
    if config.dialect and config.dialect != "auto":
        forced_dialect = Dialect(config.dialect)

    skill = parse_skill(args.path)
    if forced_dialect is not None:
        skill.dialect = forced_dialect
    findings = list(
        run_all(
            skill,
            disabled=disabled,
            severity_overrides=config.severity_overrides,
            custom_pairs=custom_pairs,
            path_overrides=config.path_overrides,
        )
    )

    from .badge import DEFAULT_BADGE_LINK, format_badge, grade_from_findings

    report = grade_from_findings(findings)
    link = args.link or DEFAULT_BADGE_LINK
    print(format_badge(report, fmt=args.format, link=link))
    return 0


def _main_init(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="doodle init",
        description=(
            "Scaffold a compliant SKILL.md (and optionally an eval.yaml). "
            "The generated file passes `doodle lint` with zero warnings out of the box."
        ),
    )
    parser.add_argument(
        "name",
        type=str,
        nargs="?",
        default=None,
        help="Skill name in kebab-case (letters, digits, hyphens).",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory to scaffold into. Defaults to ./<name>.",
    )
    parser.add_argument(
        "--dialect",
        choices=["anthropic", "extended"],
        default="anthropic",
        help="Frontmatter schema variant to generate (default: anthropic).",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        dest="include_eval",
        help="Also scaffold a starter eval.yaml for Phase 2 trigger-accuracy testing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing SKILL.md or eval.yaml files.",
    )
    parser.add_argument(
        "--author",
        default="",
        help="Author for the extended-dialect frontmatter.",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Use a category-specific starter template (see --list-templates).",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List available category templates and exit.",
    )
    args = parser.parse_args(argv)

    if args.list_templates:
        from .templates import list_templates
        for tpl in list_templates():
            print(f"  {tpl.name:<20}  {tpl.summary}")
        return 0

    if args.name is None:
        parser.print_usage(sys.stderr)
        print("doodle init: 'name' is required (or use --list-templates)", file=sys.stderr)
        return 3

    from .init import InitError, InitOptions, scaffold

    directory = args.dir if args.dir is not None else Path(args.name)
    options = InitOptions(
        name=args.name,
        directory=directory,
        dialect=args.dialect,
        include_eval=args.include_eval,
        force=args.force,
        author=args.author,
        template=args.template,
    )
    try:
        created = scaffold(options)
    except InitError as exc:
        print(f"doodle init: {exc}", file=sys.stderr)
        return 3

    print("Created:")
    for path in created:
        print(f"  {path}")
    print()
    print(f"Next: doodle {directory}/SKILL.md")
    if args.include_eval:
        print(f"      doodle eval {directory}/SKILL.md")
    return 0


def _main_eval(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="doodle eval",
        description="Trigger-accuracy harness — measures whether Claude actually invokes your skill on natural-language prompts.",
    )
    parser.add_argument("path", type=Path, help="SKILL.md, eval.yaml, or a skill directory")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Use Claude to draft a starter eval.yaml so you don't face a blank page.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Promptfoo config (or generation prompt) without running anything.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model to use for --generate (default: claude-sonnet-4-5).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path for --generate (default: eval.yaml next to the skill).",
    )
    args = parser.parse_args(argv)

    from .eval import generate_eval, run_eval
    from .eval.runner import format_eval_result

    if args.generate:
        try:
            result = generate_eval(args.path, model=args.model, dry_run=args.dry_run)
        except (FileNotFoundError, ImportError, RuntimeError, ValueError) as exc:
            print(f"doodle eval --generate: {exc}", file=sys.stderr)
            return 3
        if args.dry_run:
            sys.stdout.write("# Prompt that would be sent to Claude:\n\n")
            sys.stdout.write(result)  # type: ignore[arg-type]
            sys.stdout.write("\n")
            return 0
        out_path = args.out or (args.path.parent / "eval.yaml")
        out_path.write_text(result.dump(), encoding="utf-8")  # type: ignore[union-attr]
        sf, snf = len(result.should_fire), len(result.should_not_fire)  # type: ignore[union-attr]
        print(f"wrote {out_path} ({sf} should_fire + {snf} should_not_fire)")
        print("review and edit the file, then run: doodle eval " + str(args.path))
        return 0

    try:
        result = run_eval(args.path, dry_run=args.dry_run)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"doodle eval: {exc}", file=sys.stderr)
        return 3

    if args.dry_run:
        sys.stdout.write("# Promptfoo config that would be run:\n\n")
        sys.stdout.write(result)  # type: ignore[arg-type]
        return 0

    sys.stdout.write(format_eval_result(result))  # type: ignore[arg-type]
    return 0 if result.correct == result.total else 1  # type: ignore[union-attr]


def _main_lint(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="doodle",
        description="A linter for Claude SKILL.md files. Subcommands: lint (default), eval.",
    )
    parser.add_argument("paths", nargs="*", type=Path, help="SKILL.md files or directories to lint")
    parser.add_argument(
        "--format", choices=["text", "json", "sarif"], default="text",
        help="Output format (default: text). 'sarif' = GitHub code scanning.",
    )
    parser.add_argument(
        "--fix", action="store_true",
        help=("Apply safe auto-fixes in place, then report what's left. "
              f"Fixable rules: {', '.join(sorted(fixable_rule_ids()))}"),
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

    # Push the user allowlist into the spelling rule module
    from .rules.spelling import set_user_allowlist
    set_user_allowlist(config.spelling_allowlist)

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

    def _lint_one(path):
        skill = parse_skill(path)
        if forced_dialect is not None:
            skill.dialect = forced_dialect
        return list(
            run_all(
                skill,
                disabled=disabled,
                severity_overrides=config.severity_overrides,
                custom_pairs=custom_pairs,
                path_overrides=config.path_overrides,
            )
        )

    # If --fix, apply fixes first, then re-lint to show what's left
    fixes_applied: dict[Path, list[str]] = {}
    if args.fix:
        for path in files:
            findings = _lint_one(path)
            fired = {f.rule_id for f in findings}
            applied, _ = apply_fixes(path, fired)
            if applied:
                fixes_applied[path] = applied

    all_findings = []
    for path in files:
        all_findings.extend(_lint_one(path))

    if args.strict:
        for f in all_findings:
            if f.severity is Severity.INFO:
                f.severity = Severity.WARNING
            elif f.severity is Severity.WARNING:
                f.severity = Severity.ERROR

    use_color = False if args.no_color else None

    if args.format == "json":
        sys.stdout.write(format_json(all_findings))
    elif args.format == "sarif":
        sys.stdout.write(format_sarif(all_findings, all_rules(), __version__))
    else:
        if fixes_applied:
            sys.stdout.write("Auto-fixes applied:\n")
            for path, rules_fixed in fixes_applied.items():
                sys.stdout.write(f"  {path}: {', '.join(rules_fixed)}\n")
            sys.stdout.write("\n")
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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
