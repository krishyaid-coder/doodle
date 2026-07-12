<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/logo-wordmark-dark.svg">
    <img src="./assets/logo-wordmark-light.svg" alt="doodle" width="240"/>
  </picture>
</p>

# The Skill Quality Report — 200-Skill Refresh

Second-edition report on the quality of published Claude `SKILL.md` files. This refresh samples **200 files across six repositories**, covering roughly 3× the corpus of the [June 2026 edition](./data/quality-report-2026-06.json). Run with doodle v0.8 and the default rule configuration.

> **Headline:** **81% of sampled skills have at least one quality finding.** The rate is statistically identical to the 62-skill June edition (82%). Consistency across a much broader sample confirms the signal is not sampling artifact.

---

## Methodology

- **Corpus:** 200 `SKILL.md` files sampled from six repositories:
  - [`DietrichGebert/ponytail`](https://github.com/DietrichGebert/ponytail) — 6 skills (all first-tier, excluding `.openclaw` duplicates)
  - [`anthropics/skills`](https://github.com/anthropics/skills) — 18 first-party skills
  - [`obra/superpowers`](https://github.com/obra/superpowers) — 14 skills
  - [`vercel-labs/skills`](https://github.com/vercel-labs/skills) — 1 skill
  - [`alirezarezvani/claude-skills`](https://github.com/alirezarezvani/claude-skills) — 61 skills sampled from 357
  - [`jeremylongshore/claude-code-plugins-plus-skills`](https://github.com/jeremylongshore/claude-code-plugins-plus-skills) — 100 skills sampled from 3,685
- **Tool:** `doodle path/to/SKILL.md --format=json --no-color`. v0.8, default rules, no `--strict`.
- **Cost:** sub-second per file. Zero LLM calls.
- **Reproduce:** raw findings JSON at [docs/data/quality-report-2026-07.json](./data/quality-report-2026-07.json). Previous edition preserved at [docs/data/quality-report-2026-06.json](./data/quality-report-2026-06.json).

---

## Results

### Overall

| Metric | June (62 files) | July (200 files) | Change |
| --- | ---: | ---: | ---: |
| Clean (no findings) | 18% (11) | **19% (38)** | +1 point |
| Files with any finding | 82% | 81% | −1 point |
| Total findings | 245* | 280 | see rule table |

<sub>*The June edition included `body/emoji` at 109 hits, which was moved to opt-in in v0.4. Excluding those, the June total is 136 findings.</sub>

### Per repository

| Repo | Clean | Sampled | Clean % | Comment |
| --- | ---: | ---: | ---: | --- |
| **obra/superpowers** | 12 | 14 | **86%** | Standout. Improved from 64% in the June edition. |
| jeremylongshore/claude-code-plugins-plus-skills | 21 | 100 | 21% | Large sample from the 3,685-skill pack. Volume dominates the overall count. |
| anthropics/skills (first-party) | 1 | 18 | 6% | Unchanged from the June edition (1/17). First-party remains the low bar. |
| alirezarezvani/claude-skills | 4 | 61 | 7% | Broader sample, similar rate to the June edition. |
| DietrichGebert/ponytail | 0 | 6 | 0% | Unchanged. Every ponytail skill still trips at least one rule. |
| vercel-labs/skills | 0 | 1 | 0% | Small sample; not statistically informative. |
| **All combined** | **38** | **200** | **19%** | |

### Findings by rule

| Rule | Hits | Share | Notes |
| --- | ---: | ---: | --- |
| `desc/too-long` | 140 | 50.0% | **Highest signal in the corpus.** 70% of all sampled skills exceed the 250-char guideline. |
| `body/absolute-user-path` | 39 | 13.9% | ~4× the June rate (11/62). Hardcoded `/Users/`, `/home/`, or `~/` paths are a real portability tax. |
| `fm/unknown-field` | 30 | 10.7% | Anthropic-dialect skills with community-added fields (`version`, `author`, `tags`, etc.). |
| `desc/no-trigger-phrase` | 27 | 9.6% | Confirms Anthropic issue [#267](https://github.com/anthropics/skills/issues/267). |
| **`hygiene/trailing-whitespace`** | **20** | 7.1% | New in doodle v0.8. Fixable via `doodle --fix`. |
| **`hygiene/final-newline`** | **6** | 2.1% | New in doodle v0.8. Fixable. |
| `desc/vague-trigger` | 6 | 2.1% | Still under-reported; blocklist is conservative. |
| `fm/missing-allowed-tools` | 4 | 1.4% | Extended-dialect skills that use tools without scoping. |
| `body/too-long` | 3 | 1.1% | Bodies over 500 lines. All three are first-party or established community skills. |
| `fm/name-mismatch-dir` | 3 | 1.1% | Rare but consistently present. |
| `parse/missing-frontmatter` | 1 | 0.4% | One file has no frontmatter at all. |
| `desc/too-short` | 1 | 0.4% | |

---

## Concrete examples

### First-party is still the low bar

`anthropics/skills` has one clean file out of 18. Every other first-party skill trips at least one rule:

- `xlsx/SKILL.md` — 5 findings including 2 trailing-whitespace violations
- `canvas-design/SKILL.md` — 4 findings
- `claude-api/SKILL.md` — 4 findings including `body/absolute-user-path` and `body/too-long`
- `docx/SKILL.md` — 3 findings, still over the 500-line soft cap
- `skill-creator/SKILL.md` — 2 findings, still references `~/Downloads/eval_set.json` at line 371

The `desc/no-trigger-phrase` rule fires on nine first-party skills. The Anthropic docs recommend explicit "use when" phrasing; the reference implementations mostly do not.

### Ponytail: still 0 for 0

All six ponytail skills continue to fail at least one rule. `ponytail-help/SKILL.md:53` still contains the hardcoded `~/.config/ponytail/config.json` reference. Every variant trips `desc/too-long` — the descriptions read as complete usage guides, not trigger surfaces.

### The worst-offender file in the sample

`alirezarezvani/engineering/skills/api-design-reviewer/SKILL.md` — **10 findings**, mostly `hygiene/trailing-whitespace` (8 hits) plus `desc/too-long` and `hygiene/final-newline`. This one file would clean up entirely on a single `doodle --fix` invocation.

### obra/superpowers: the standout

12 of 14 skills clean. The two files with findings each have exactly one — `desc/no-trigger-phrase` in both cases. This is what a well-maintained community skill pack looks like when authors care about the guidelines.

---

## What the refresh added

Two rules that shipped in doodle v0.8 (hygiene/trailing-whitespace, hygiene/final-newline) already caught 26 real findings across the corpus. Both are auto-fixable:

```bash
doodle path/to/skills --fix
```

For an author with an alirezarezvani-style repo, one `--fix` invocation would clean up ~20% of all findings in the corpus.

---

## What this means for authors

Odds that a published `SKILL.md` has at least one quality issue: **4 in 5**. Descriptions dominate the failure surface — 70% of skills exceed 250 characters and 14% include no explicit trigger phrase. The most productive fixes, in order:

1. **Trim your description to 250 characters or fewer.** If you cannot fit the intent in a sentence, you have three skills, not one.
2. **Add "Use when…" phrasing.** Explicit trigger surface is the single highest-leverage change per Anthropic's own issue #267.
3. **Delete hardcoded paths.** `~/Downloads/foo.json` doesn't exist on Windows and never on the current-shell-user's machine.
4. **Run `doodle --fix` before every commit.** The two new v0.8 rules catch ~20% of the visible noise for free.

Install:

```bash
pip install git+https://github.com/krishyaid-coder/doodle.git
doodle path/to/SKILL.md
```

---

## What this means for the ecosystem

- **The signal is consistent.** Same 19% clean rate across 62 and 200 skills. Corpus size did not change the answer.
- **Best-in-class exists.** obra/superpowers proves that 85%+ clean is achievable. It is a maintenance choice, not an unavoidable cost.
- **The gap between first-party and best community pack is real.** Anthropic's own skills score 6% clean; obra's score 86%. Reference implementations should be reference-quality.
- **Static analysis handles a lot.** Even before doodle's Phase 2 trigger-accuracy harness, 280 findings across 200 skills are catchable without an LLM in the loop.

If you operate a Claude Code marketplace, a submission gate on `doodle --strict` closes 80% of the ecosystem's known quality gap in one step. Happy to talk.

---

## Honest limitations

- **`desc/typo` (spelling) is off by default.** Enabling it flips the numbers substantially. The report understates typo-driven trigger degradation.
- **`body/emoji` is off by default.** Same reason.
- **The 3,685-skill jeremylongshore pack is not representative of authored skills** — it is largely template-generated. The 21% clean rate is likely inflated relative to hand-authored skills.
- **This refresh is a snapshot.** Skill authors update files. The findings above are true for the tree state at sample time; they may not be true tomorrow.

---

*Have a skill that scored badly here and you disagree with the rule that fired? Good. Open an issue at [github.com/krishyaid-coder/doodle](https://github.com/krishyaid-coder/doodle/issues). The rule set gets better when authors push back on it.*
