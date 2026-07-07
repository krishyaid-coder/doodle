"""desc/typo — flag likely misspellings in the description field.

Rationale: descriptions are the primary trigger surface. A misspelling in the
description means Claude's automatic skill-picker matches the misspelled token,
but users type the correctly-spelled version, and the skill silently fails to
fire. The token-cost effect of typos is negligible; the trigger-match
degradation is the real bill.

Implementation:
    * ``pyspellchecker`` provides a ~160k-word English dictionary.
    * A built-in allowlist covers AI, developer, and Claude-ecosystem vocabulary
      that would otherwise trigger false positives.
    * Users extend the allowlist via ``[spelling] allow = [...]`` in
      ``.doodle.toml``.
    * Words with any non-alphabetic character (digits, dashes, dots) are skipped
      because they are almost always identifiers, filenames, or code.
    * Runs on the description field only. Body checking would need code-fence /
      table / URL handling and is deferred until v0.7 at earliest.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache

from ..models import Dialect, Finding, ParsedSkill, Rule, Severity


_BOTH = frozenset({Dialect.ANTHROPIC, Dialect.EXTENDED})

# Words that pyspellchecker's stock English dictionary flags but that appear
# in almost every Claude-adjacent SKILL.md. Kept lowercase; the check is
# case-insensitive. This list is deliberately conservative — adding niche jargon
# here weakens the signal.
BUILTIN_ALLOWLIST: frozenset[str] = frozenset(
    w.lower()
    for w in [
        # Anthropic products
        "Anthropic", "Claude", "Sonnet", "Haiku", "Opus",
        # AI / ML general
        "LLM", "LLMs", "GPT", "AI", "ML", "NLP", "RLHF", "AGI", "RAG",
        "prompt", "prompts", "prompting", "tokenizer", "tokenizers", "tokens",
        "embedding", "embeddings", "hyperparameter", "hyperparameters",
        "multimodal",
        # Skills ecosystem
        "SKILL", "SKILLs", "Promptfoo", "MCP", "OpenAI", "Anthropic's",
        # Dev tooling
        "CLI", "SDK", "API", "GUI", "IDE", "GitHub", "GitLab", "Bitbucket",
        "OAuth", "JWT", "HTTPS", "HTTP", "SSL", "TLS", "URL", "URI",
        "REST", "GraphQL", "WebSocket", "gRPC", "SSE",
        "SARIF", "YAML", "TOML", "JSON", "XML", "HTML", "CSS", "SQL", "TSV",
        "CSV", "MDX", "SVG", "PDF", "PNG", "JPG", "JPEG",
        "README", "SKILL.md", "PR", "PRs", "CI", "CD", "TDD", "BDD",
        # Languages / runtimes
        "Python", "TypeScript", "JavaScript", "Rust", "Golang", "Kotlin",
        "Swift", "Ruby", "PHP", "Elixir", "Erlang", "Haskell", "Clojure",
        "Node.js", "Deno", "Bun", "Django", "Flask", "FastAPI", "React",
        "Vue", "Svelte", "Angular", "Next.js", "Nuxt", "Astro",
        # Package managers / build tools
        "npm", "pnpm", "yarn", "pip", "pipx", "poetry", "uv", "cargo",
        "webpack", "vite", "esbuild", "rollup", "turbopack",
        # Cloud / infra
        "Kubernetes", "Docker", "AWS", "GCP", "Azure", "CloudFlare",
        "Terraform", "Ansible", "Vercel", "Netlify", "Heroku", "Fly.io",
        "Supabase", "Postgres", "PostgreSQL", "MySQL", "SQLite", "Redis",
        "MongoDB", "DynamoDB", "Kafka", "RabbitMQ",
        # Operating systems / shells
        "macOS", "Linux", "Windows", "iOS", "Android", "POSIX", "Unix",
        "bash", "zsh", "fish", "PowerShell",
        # Misc common in dev docs
        "changelog", "cronjob", "workflow", "workflows", "middleware",
        "microservice", "microservices", "monorepo", "polyrepo",
        "namespace", "namespaces", "boilerplate", "linter", "linters",
        "linting", "codebase", "codebases", "refactor", "refactors",
        "refactoring", "async", "await", "callback", "callbacks",
        "webhook", "webhooks", "throttle", "rate-limit",
        "auth", "authn", "authz", "SSO", "MFA", "TOTP",
        # Dev slang / abbreviations pyspellchecker misses
        "diff", "diffs", "config", "configs", "params", "arg", "args",
        "kwargs", "regex", "regexes", "stdout", "stderr", "stdin",
        "sudo", "iframe", "iframes", "hostname", "hostnames",
        "runtime", "runtimes", "compiler", "compilers", "interpreter",
        "interpreters", "backend", "backends", "frontend", "frontends",
        "fullstack", "sysadmin", "devops", "mlops",
        "commit", "commits", "committer", "rebase", "cherry-pick",
        "pushed", "pulled", "branch", "branches", "merged", "merging",
        "unmerged",
    ]
)


# User allowlist set from ``.doodle.toml`` at CLI startup. Kept as a module
# global so the check function stays a plain ``(skill, rule) -> findings``
# callable and we don't have to widen the checker signature.
_user_allowlist: frozenset[str] = frozenset()


def set_user_allowlist(allow: object) -> None:
    """Populate the user-provided allowlist. Called from the CLI after config
    is loaded. Accepts any iterable of strings; case is normalized."""
    global _user_allowlist
    if not allow:
        _user_allowlist = frozenset()
        return
    _user_allowlist = frozenset(str(w).lower() for w in allow)


@lru_cache(maxsize=1)
def _get_spellchecker():
    """Lazy-load pyspellchecker so the rule is a no-op when the package
    isn't installed. Returns None if the dependency is missing."""
    try:
        from spellchecker import SpellChecker  # type: ignore
    except ImportError:
        return None
    return SpellChecker()


# Match alphabetic words, optionally with an internal or trailing apostrophe
# (handles "Anthropic's", "don't"). Excludes anything with digits, dashes,
# dots, underscores — those are almost always identifiers, code, or filenames.
_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def _tokenize(text: str) -> list[tuple[str, int]]:
    """Return ``(word, column)`` pairs. Column is 1-indexed."""
    return [(m.group(0), m.start() + 1) for m in _WORD_RE.finditer(text)]


def check_typo(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    desc = skill.frontmatter.get("description")
    if not isinstance(desc, str) or not desc.strip():
        return

    sc = _get_spellchecker()
    if sc is None:
        # pyspellchecker not installed — surface a single info-level notice
        # so users know why the rule isn't firing, rather than staying silent.
        yield Finding(
            rule_id=rule.id,
            severity=Severity.INFO,
            file=skill.path,
            line=skill.frontmatter_field_line("description"),
            column=1,
            message=(
                "desc/typo requires 'pyspellchecker'. Install with: "
                "pip install pyspellchecker"
            ),
        )
        return

    combined = BUILTIN_ALLOWLIST | _user_allowlist

    line_no = skill.frontmatter_field_line("description")
    misspelled_seen: set[str] = set()

    for word, column in _tokenize(desc):
        # Strip possessive suffix for the check ("Anthropic's" -> "Anthropic")
        base = word.split("'", 1)[0]
        lowered = base.lower()

        if lowered in combined:
            continue
        # Skip single-letter tokens; too noisy
        if len(base) < 2:
            continue

        if base.lower() in sc:
            continue

        if lowered in misspelled_seen:
            continue
        misspelled_seen.add(lowered)

        # Best-guess correction (may be None if pyspellchecker has no candidate)
        correction = sc.correction(base.lower())
        suggestion = None
        if correction and correction != base.lower():
            suggestion = f"Did you mean {correction!r}?"

        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=line_no,
            column=column,
            message=(
                f"Description contains a likely misspelling: {base!r}. "
                "Typos in descriptions degrade trigger matching — users type "
                "the correctly-spelled form."
            ),
            suggestion=suggestion,
        )


RULES = [
    Rule(
        id="desc/typo",
        title="Description contains a likely misspelling",
        severity=Severity.INFO,
        category="description",
        dialects=_BOTH,
        default_enabled=False,  # Domain vocabulary varies; ship opt-in and let users curate allowlists.
        citation="https://github.com/krishyaid-coder/doodle/blob/main/docs/RULES.md#desc-typo",
    ),
]

CHECKS = [
    (RULES[0], check_typo),
]
