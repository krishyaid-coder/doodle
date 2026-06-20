<p align="center">
  <img src="./assets/logo-wordmark.svg" alt="doodle" width="240"/>
</p>

# The Skill Quality Report

A first look at quality issues across 62 published Claude `SKILL.md` files from the top community and first-party repos. Run with doodle v0.2 in June 2026.

> **Headline:** **82% of famous skills have at least one quality finding.** First-party isn't immune. Even ponytail — the 33k-star reference skill — trips four of our rules.

---

## Methodology

- **Corpus:** 62 `SKILL.md` files sampled from:
  - [`DietrichGebert/ponytail`](https://github.com/DietrichGebert/ponytail) — 6 skills
  - [`anthropics/skills`](https://github.com/anthropics/skills) — 17 first-party skills
  - [`obra/superpowers`](https://github.com/obra/superpowers) — 14 skills
  - [`alirezarezvani/claude-skills`](https://github.com/alirezarezvani/claude-skills) — top 25 sampled
- **Tool:** `doodle path/to/SKILL.md --format=json --no-color`. v0.2, default config, no `--strict`.
- **Cost:** sub-second per file. Zero LLM calls.
- **Reproduce:** the [raw results JSON](https://github.com/krishyaid-coder/doodle/tree/main/docs/data/quality-report-2026-06.json) is in this repo.

---

## Results

| Repo | Clean | Total | Clean % | Notes |
|---|---:|---:|---:|---|
| **obra/superpowers** | 9 | 14 | **64%** | Clear quality outlier. Tight descriptions, modest bodies. |
| **anthropics/skills** (first-party) | 1 | 17 | 6% | Mostly long descriptions and oversized bodies. First-party isn't exempt. |
| **alirezarezvani/claude-skills** | 1 | 25 | 4% | Largest absolute number of findings. |
| **DietrichGebert/ponytail** | 0 | 6 | **0%** | Every skill trips `desc/too-long`; one has a hardcoded user path. |
| **All combined** | **11** | **62** | **18%** | — |

### Findings by rule

| Rule | Hits | Signal vs noise |
|---|---:|---|
| `body/emoji` | 109 | High volume — emoji is everywhere. Calibration confirmed: ships as `info`, not `warning`. |
| `desc/too-long` | 39 | **Highest signal.** Hits anthropic, ponytail, and community. |
| `desc/no-trigger-phrase` | 15 | Confirms Anthropic issue [#267](https://github.com/anthropics/skills/issues/267). |
| `fm/unknown-field` | 15 | Surfaces a dialect detection gap (see "What we learned" below). |
| `body/absolute-user-path` | 11 | **Real portability bugs.** Skills break on other users' machines. |
| `desc/vague-trigger` | 3 | Lower than expected; blocklist may be too narrow. |
| `body/too-long` | 2 | Calibrated well — catches `docx` and `skill-creator`. |
| Others | 4 | `parse/missing-frontmatter`, `desc/too-short`, `fm/name-mismatch-dir`, `fm/missing-allowed-tools`. |

---

## Concrete examples

### Ponytail itself — the most famous skill on the platform

> `ponytail/skills/ponytail/SKILL.md`

```
desc/too-long          Description is 606 characters (max 250).
body/absolute-user-path (in ponytail-help/SKILL.md, line 51)
                       '~/.config/ponytail/config.json' — breaks on Windows.
```

Every variant — `ponytail`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help`, `ponytail-review` — trips at least one rule. The most-installed skill on the platform isn't a clean exemplar.

### First-party isn't exempt

> `anthropics/skills/skills/mcp-builder/SKILL.md` — 13 findings (mostly emoji + a long description).
> `anthropics/skills/skills/docx/SKILL.md` — long description + body over the 500-line soft cap.

The hard `body/way-too-long` (1500-line) rule does not fire — Anthropic's bodies are large but not pathological. The soft cap exists for a reason though, and the official files do trip it.

### Community skills, worst offenders

> `obra-superpowers/skills/writing-skills/SKILL.md` — **16 findings**.  
> `alirezarezvani/.gemini/skills/TEMPLATE/SKILL.md` — **15 findings**.  
> `alirezarezvani/.gemini/skills/agent-protocol/SKILL.md` — **15 findings**.

Three patterns recur: emoji density, long descriptions, and (in community packs) extra frontmatter fields that suggest a non-Anthropic dialect.

---

## What we learned (about doodle)

This report is honest about the tool's own limitations:

1. **`body/emoji` at 109 hits is noise, not signal.** Defaulting to `info` was correct. We will not promote it. Users who care can enable via `--strict` or override severity in config.
2. **`fm/unknown-field` may need a Gemini-style dialect.** The 15 hits cluster in `.gemini/skills/` files using fields like `color` and `emoji`. These aren't Anthropic skills — they're cross-agent skills using a different schema. The right fix is a `gemini` dialect, not a rule change. Tracked.
3. **`desc/vague-trigger` may be too narrow.** Only 3 hits. The blocklist needs more phrases — we'll expand it from real corpus evidence (this report is the start of that dataset).
4. **`parse/missing-frontmatter` caught a README masquerading as `SKILL.md`** at `.gemini/skills/README/SKILL.md`. Not a bug; the file is real-world misuse. Worth noting in docs.

---

## What this means for skill authors

If you publish a `SKILL.md`, your odds of having at least one quality issue are **~4 in 5**. The most common, in order:

1. Description longer than 250 characters → trim to the essential "what" + concrete trigger phrases.
2. No explicit "use when…" phrasing → add one. It is the highest-leverage fix per Anthropic's own data.
3. Hardcoded `/Users/...` or `~/...` paths → use config vars or document the path as user-provided.
4. Bodies over 500 lines → split into multiple skills, or move detail into separate referenced files.

**Fix yours in 30 seconds:**

```bash
pip install doodle-lint
doodle path/to/SKILL.md
```

Get the lint report. Apply the suggestions. Done.

---

## What this means for the ecosystem

- **There is no quality bar today.** Even the most popular skills ship issues that take seconds to detect.
- **Static checks alone catch a lot.** No LLM calls were involved in any of the 51 flagged files.
- **Trigger-accuracy is still the bigger half.** Anthropic's [issue #267](https://github.com/anthropics/skills/issues/267) attributes 80% of failures to *vague descriptions*, which static rules catch only partially. Phase 2 of doodle (a Promptfoo-based eval) is where the rest lives.

If you operate a Claude Code marketplace, a CI gate using `doodle --strict` lifts the floor immediately. We're [open to talking](https://github.com/krishyaid-coder/doodle/issues) about adoption.

---

*Have a skill that scored badly here and you'd like to argue with the rule? Good — open an issue. Every rule in doodle is supposed to be falsifiable, and the corpus that informs them grows with you in it.*
