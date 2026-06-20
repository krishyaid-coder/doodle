# Extending doodle

How to add a rule, a category, a dialect, or a formatter. Each section is self-contained.

If you're proposing a new rule, please [open an issue](https://github.com/krishyaid-coder/doodle/issues) first with the evidence — in-sample frequency, citation, false-positive risk. The bar is "real authors will thank us for this," not "it'd be cool."

---

## Add a rule (12 lines)

Rules live in `src/doodle/rules/<category>.py`. Each rule is two values: metadata (`Rule`) and a checker function. Append both to the module's `RULES` and `CHECKS` lists.

```python
# src/doodle/rules/description.py

def check_my_new_rule(skill: ParsedSkill, rule: Rule) -> Iterable[Finding]:
    desc, line = _get_description(skill)
    if not desc:
        return
    if "bad thing" in desc.lower():
        yield Finding(
            rule_id=rule.id,
            severity=rule.severity,
            file=skill.path,
            line=line,
            column=1,
            message="Description contains 'bad thing'.",
            suggestion="Use 'good thing' instead.",
        )

RULES.append(
    Rule(
        id="desc/no-bad-thing",
        title="Description should not contain 'bad thing'",
        severity=Severity.WARNING,
        category="description",
        dialects=_BOTH,
        citation="https://github.com/anthropics/skills/issues/123",
    )
)
CHECKS.append((RULES[-1], check_my_new_rule))
```

Then write a fixture and a test:

```python
# tests/fixtures/desc-bad-thing/SKILL.md
---
name: desc-bad-thing
description: Does the bad thing when invoked.
---
# body
```

```python
# tests/test_rules.py
def test_no_bad_thing_fires():
    ids = _ids(_findings("desc-bad-thing"))
    assert "desc/no-bad-thing" in ids
```

Run `pytest`. If green, you're done.

---

## Rule quality checklist

Before opening a PR, the rule must clear all five:

- [ ] **Citation.** A link to Anthropic docs, a community issue, or a documented sample. No "I think this is bad."
- [ ] **In-sample frequency.** What fraction of a representative sample triggers it? If zero, it's premature; park it in the deferred list.
- [ ] **False-positive estimate.** Walk through 5 published skills mentally. How many would trip falsely?
- [ ] **Severity justification.** `error` only if the skill will fail to load or trigger. `warning` is the default. `info` is style.
- [ ] **Suggestion is concrete.** Telling someone "your description is bad" is useless. Tell them what to do instead.

---

## Add a category

```python
# src/doodle/rules/security.py
from ..models import Dialect, Finding, ParsedSkill, Rule, Severity

_BOTH = frozenset({Dialect.ANTHROPIC, Dialect.EXTENDED})

RULES: list[Rule] = []
CHECKS: list = []

# define rules and checkers here, then append to lists
```

Then wire it into the registry:

```python
# src/doodle/rules/__init__.py
from . import body, description, frontmatter, hygiene, security  # add security
_MODULES = [description, body, frontmatter, hygiene, security]    # add security
```

That's it.

---

## Add a dialect

A dialect is "a recognized `SKILL.md` schema variant." We have two today: `anthropic` (minimal) and `extended` (community). New agent ecosystems (Codex skills, Cursor rules, Gemini Gems) may want their own.

Three changes:

```python
# src/doodle/models.py
class Dialect(str, Enum):
    ANTHROPIC = "anthropic"
    EXTENDED = "extended"
    CODEX = "codex"    # new
```

```python
# src/doodle/parser.py
CODEX_HINT_FIELDS = frozenset({"codex-version", "...."})

def detect_dialect(fm: dict[str, Any]) -> Dialect:
    if any(k in fm for k in CODEX_HINT_FIELDS):
        return Dialect.CODEX
    if any(k in fm for k in EXTENDED_HINT_FIELDS):
        return Dialect.EXTENDED
    return Dialect.ANTHROPIC
```

Then mark each rule's `dialects=` set to include or exclude the new dialect. Rules that don't apply to a dialect are silently skipped by the registry.

Add an entry to the `--dialect` flag's choices in `cli.py` if you want users to be able to force it.

---

## Add a custom rule via config (no Python required)

For enterprise / team-specific rules, you don't need to touch the codebase. Drop a `.doodle.toml` in your project root.

### Pattern rule (regex over body, description, or name)

```toml
[[rules]]
id = "acme/no-customer-pii"
kind = "pattern"
pattern = "(?i)\\bcustomer_[a-z]+\\b"
applies-to = "body"            # body | description | name
severity = "error"             # info | warning | error
message = "Customer PII tokens are not allowed in skills."
suggestion = "Use 'user_<role>' instead."
```

### Frontmatter-required rule

```toml
[[rules]]
id = "acme/require-team-tag"
kind = "frontmatter-required"
fields = ["team", "data-classification"]
severity = "error"
message = "Internal skills must declare 'team' and 'data-classification'."
```

### Disable or change severity of any rule (built-in or custom)

```toml
[severity]
"body/emoji" = "off"           # disabled entirely
"body/too-long" = "info"       # downgrade
"desc/vague-trigger" = "error" # promote
```

### Per-path overrides (glob)

```toml
[[paths]]
glob = "**/experiments/**/SKILL.md"
disabled = ["desc/vague-trigger", "body/too-long"]
```

### Full example

```toml
[options]
dialect = "extended"           # auto | anthropic | extended
fail-on = "warning"            # error | warning | never

[severity]
"body/emoji" = "off"

[[paths]]
glob = "**/experiments/**/SKILL.md"
disabled = ["body/too-long"]

[[rules]]
id = "acme/no-customer-pii"
kind = "pattern"
pattern = "(?i)\\bcustomer_[a-z]+\\b"
applies-to = "body"
severity = "error"
message = "Customer PII tokens are not allowed in skills."

[[rules]]
id = "acme/require-team-tag"
kind = "frontmatter-required"
fields = ["team", "data-classification"]
severity = "error"
message = "Internal skills must declare team and data-classification."
```

doodle discovers `.doodle.toml` by walking up from the working directory. You can also embed config under `[tool.doodle]` in `pyproject.toml`. Force a path with `--config`.

When config rules aren't enough — you need real Python logic — fall back to the Python-rule path above.

---

## Add a formatter

```python
# src/doodle/formatters.py
def format_sarif(findings: list[Finding]) -> str:
    """SARIF 2.1.0 for GitHub code scanning."""
    payload = { "$schema": "...", "version": "2.1.0", "runs": [...] }
    return json.dumps(payload, indent=2) + "\n"
```

Wire it:

```python
# src/doodle/cli.py
parser.add_argument("--format", choices=["text", "json", "sarif"], default="text")
# ...
if args.format == "sarif":
    sys.stdout.write(format_sarif(all_findings))
```

Done.

---

## How tests are organized

- `tests/fixtures/<scenario>/SKILL.md` — one fixture per scenario. Keep them small and single-purpose.
- `tests/test_rules.py` — one test per rule scenario. Helper `_findings(name)` runs the full pipeline; `_ids(findings)` returns the set of fired rule IDs.

Rule of thumb: if a fixture is more than 30 lines, it's probably testing too many things at once.

---

## Local development loop

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                # full suite, < 1s
pytest tests/test_rules.py::test_good_skill_has_no_findings -v   # single test
doodle tests/fixtures/                # eyeball CLI output
doodle --list-rules                   # see everything registered
doodle --explain desc/too-long        # confirm a rule's metadata renders
```

---

## What we won't merge (without convincing evidence)

- **LLM-call rules.** v0 is deterministic by design. If you want a rule that needs Claude to fire, it belongs in Phase 2 `doodle eval`, not in `lint`.
- **Style preferences with no citation.** "I prefer two blank lines before headings" is not a rule.
- **Rules that double-count an existing rule's failure modes.** Consolidate or pick the sharper one.
- **Rules with > 20% estimated false positives on real skills.** They erode trust faster than they add value.

When in doubt, open an issue first. We'd rather talk about evidence than reject a PR.
