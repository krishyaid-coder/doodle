# doodle — v0 Rule Specification

A static linter for Claude `SKILL.md` files. Rules below are grounded in 19 real-world samples and Anthropic's official authoring guide.

---

## Severity levels

| Level | Meaning | Default exit-code impact |
|---|---|---|
| `error` | The skill will likely fail to load or trigger correctly, OR violates a hard cap. | exit 2 |
| `warning` | The skill is parseable but quality is degraded — vague triggers, oversized body, missing scoping. | exit 1 (configurable) |
| `info` | Style / consistency / hygiene. No functional impact. | exit 0 |

---

## Dialect handling

Two SKILL.md dialects exist in the wild:

- **`anthropic`** — minimal frontmatter: `name`, `description`, optional `license`. Used by `anthropics/skills` and `vercel-labs/skills`.
- **`extended`** — community schema with `version`, `author`, `tags`, `allowed-tools`, `compatible-with`. Used by `jeremylongshore/*`, `alirezarezvani/*`, `DietrichGebert/ponytail`.

doodle auto-detects dialect by frontmatter shape; users can force with `--dialect=anthropic|extended`. Some rules apply to both; some are dialect-scoped (noted per rule).

---

## v0 ruleset (12 rules)

### Category: description

#### `desc/too-long` — warning
**Both dialects.** Description exceeds 250 characters (Anthropic's documented cap).

- Why: descriptions are the primary trigger signal; overlong descriptions dilute matching and waste context budget.
- Citation: [docs.claude.com — best-practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)
- In-sample frequency: **8/19** (incl. ponytail, docx, aeo at 770 chars)
- Fail: `description: "Answer Engine Optimization expert specializing in optimizing content for LLM citation and discovery across AI assistants. Use when conducting AEO audits, analyzing brand visibility in AI responses, optimizing content for citation by ChatGPT/Claude/Gemini/Perplexity, tracking AI mentions, building entity-based content strategies, ..."` (770 chars)
- Pass: `description: "Reviews staged Python diffs for security and correctness. Use when the user says 'review my changes' or runs git diff."` (123 chars)

#### `desc/too-short` — warning
**Both dialects.** Description under 60 characters.

- Why: too short means the trigger surface is thin — Claude has no keywords to match against.
- In-sample frequency: 2/19
- Fail: `description: "Use when creating new skills."` (32 chars)
- Pass: see above

#### `desc/no-trigger-phrase` — warning
**Both dialects.** Description lacks any "Use when…", "Trigger with…", "When the user…" phrasing, OR has no quoted/concrete user phrases.

- Why: Anthropic issue [#267](https://github.com/anthropics/skills/issues/267) attributes 80% of trigger failures to vague descriptions. Concrete trigger phrases are the highest-leverage fix.
- In-sample frequency: 5/19
- Fail: `description: "A senior data engineer that designs ETL pipelines."`
- Pass: `description: "Designs ETL pipelines. Use when the user says 'design a pipeline', 'data architecture', or mentions Airflow/dbt/Spark."`

#### `desc/vague-trigger` — warning
**Both dialects.** Description's trigger phrases overlap Claude's default behavior. Curated blocklist v0: `"reviewing code"`, `"reviewing pull requests"`, `"writing tests"`, `"writing code"`, `"building a feature"`, `"debugging"`, `"answering questions"`, `"general programming"`.

- Why: per Anthropic [#267](https://github.com/anthropics/skills/issues/267), 30% of trigger failures are conflicting/overlapping triggers — the skill never fires because Claude handles the case natively.
- In-sample frequency: 3/19 (code-reviewer, senior-data-engineer, using-superpowers)
- Configurable: users can extend the blocklist via `.doodle.toml`.

---

### Category: body

#### `body/too-long` — warning
**Both dialects.** Body exceeds 500 lines.

- Why: Anthropic's guide caps at ~500 lines for progressive-disclosure reasons; longer bodies bloat agent context on every load.
- In-sample frequency: 5/19 (incl. first-party `skill-creator` at 1247 and `docx` at 1047)
- Caveat: first-party violations suggest 500 is *aspirational* — we ship as `warning`, not `error`.

#### `body/way-too-long` — error
**Both dialects.** Body exceeds 1500 lines.

- Why: at this length the skill is almost certainly a doc dump, not a triggerable instruction set.
- In-sample frequency: 0/19 in our sample. Ships as a safety cap.

#### `body/absolute-user-path` — warning
**Both dialects.** Body contains `/Users/`, `/home/`, or `~/` outside fenced code blocks.

- Why: hardcoded paths from the author's machine break portability when others install the skill.
- In-sample frequency: 2/19 (skill-creator references `~/Downloads/eval_set.json`; aeo uses `~/.aeo-data/citations.json`).
- Implementation note: skip matches inside ```` ``` ```` fences to allow shell examples.

#### `body/emoji` — info
**Both dialects.** Body contains emoji characters.

- Why: Anthropic style guide discourages emoji in skill bodies; keeps tone consistent with default agent behavior.
- In-sample frequency: 1/19 (ponytail-review uses ❌ in examples).
- Off by default; enable via `--strict` or config.

---

### Category: frontmatter

#### `fm/name-mismatch-dir` — warning
**Both dialects.** `name:` field doesn't match the parent directory name.

- Why: Claude resolves skills by directory; a mismatch causes the skill to load under the wrong identifier.
- In-sample frequency: 0/19 in the sample — but the rule is cheap and prevents a class of confusing bugs.

#### `fm/missing-allowed-tools` — warning
**`extended` dialect only.** Body invokes Bash/Write/Edit verbs but `allowed-tools` is absent.

- Why: explicit tool scoping limits blast radius; the `extended` dialect treats it as required.
- In-sample frequency: 9/19 community skills omit it.
- Heuristic v0: flag if body contains any of `Bash`, `Write`, `Edit`, `subprocess`, `os.system`, `shell` AND `allowed-tools` is missing.

#### `fm/unknown-field` — info
**`anthropic` dialect only.** Frontmatter contains fields outside `{name, description, license}`.

- Why: anthropic-dialect skills should stay minimal; unknown fields suggest the file targeted a different runtime.
- Configurable allowlist via `.doodle.toml`.

---

### Category: hygiene

#### `hygiene/desc-blank-lines` — info
**Both dialects.** Description (when written as YAML folded/block scalar) contains literal blank lines.

- Why: multi-line YAML descriptions silently inject `\n\n` into the loaded string, which may degrade trigger matching.
- In-sample frequency: 3/19 (stored-procedures, intercom, clickup packs).

---

## Rule schema (internal representation)

```python
@dataclass
class Rule:
    id: str                    # e.g. "desc/too-long"
    title: str
    severity: Severity         # error | warning | info
    category: str              # description | body | frontmatter | hygiene
    dialects: set[Dialect]     # {anthropic, extended} or subset
    citation: str | None       # URL or issue ref
    fixable: bool              # v1 — does --fix know how to repair this?

    def check(self, skill: ParsedSkill) -> Iterable[Finding]: ...
```

```python
@dataclass
class Finding:
    rule_id: str
    severity: Severity
    file: Path
    line: int                  # 1-indexed; 0 means file-level
    column: int                # 1-indexed; 0 means line-level
    message: str
    suggestion: str | None     # human-readable fix hint
```

---

## CLI surface (v0)

```
doodle <path>                      # lint a file or directory (recursive)
doodle --format=text|json|sarif    # output format
doodle --dialect=anthropic|extended|auto
doodle --strict                    # promote info → warning, warning → error
doodle --config=.doodle.toml
doodle --ignore=desc/too-long      # disable rules
doodle --explain desc/too-long     # print rule docs to stdout
doodle --version
```

Exit codes:
- `0` — no findings, or only `info`
- `1` — warnings present
- `2` — errors present
- `3` — tool error (file not found, invalid YAML, etc.)

---

## Custom rules (v0.2)

Beyond the 12 built-ins, users can declare project-specific rules in `.doodle.toml`:

- **`kind = "pattern"`** — regex over `body`, `description`, or `name`.
- **`kind = "frontmatter-required"`** — assert a list of frontmatter fields exists.
- **`[severity]`** — disable or change severity of any rule (built-in or custom).
- **`[[paths]]`** — per-glob disables.

Full schema and examples: [docs/EXTENDING.md](./docs/EXTENDING.md#add-a-custom-rule-via-config-no-python-required).

---

## Out of scope for v0 (deferred)

- **Trigger-accuracy eval (Phase 2)** — wraps Promptfoo's `skill-used` assertion. Separate command (`doodle eval`).
- **`--fix` auto-repair** — needs per-rule fixers. v1.
- **VS Code / Claude Code extension** — v1+.
- **Web playground** — depends on traction.
- **`body/redundant-with-frontmatter`** — needs semantic similarity, not pure static analysis. Defer.
- **`desc/first-person`** — zero in-sample frequency; defer until evidence appears.

---

## Open questions

1. Should `body/too-long` count code-fence content toward the line cap, or just prose? Anthropic's guide is silent.
2. Default for `body/emoji` — info or warning? First-party skills (anthropics/frontend-design) use no emoji, but adoption is mixed.
3. For `fm/missing-allowed-tools`, the `anthropic` dialect doesn't require the field at all — should we add a separate `--require-tool-scoping` flag, or only flag for `extended`?
4. Should doodle fail-fast on unparseable YAML frontmatter, or emit it as `error` and continue scanning the body? (eslint continues; pyflakes stops.)
