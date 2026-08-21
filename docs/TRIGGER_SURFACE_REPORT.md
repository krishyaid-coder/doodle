<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/logo-wordmark-dark.svg">
    <img src="./assets/logo-wordmark-light.svg" alt="doodle" width="240"/>
  </picture>
</p>

# The Trigger Surface Report

Published agent skills are usually judged on the *form* of their description: is it short enough, does it use third person, does it contain the phrase "use when". Those are the checks every SKILL.md linter performs, including doodle's own.

This report asks a different question. **Does the description use the words people actually type?**

> **Headline:** across 77 published skills, descriptions shared a mean of **24%** of their vocabulary with realistic user phrasings. **57%** matched requests they should ignore as well as, or better than, their own. And description length — the single most commonly enforced rule in this space — explains under **8%** of the variance in that overlap.

---

## Why vocabulary overlap matters

Skill selection is a matching problem. The user types something; the agent compares it against the descriptions of every installed skill and picks one.

A description can be perfectly formed and still lose every match:

```
description: Performs heuristic evaluation of committed changesets.
user types:  "check my code"
overlap:     0%
```

Nothing in that description is wrong. It is the right length, third person, specific. It will simply never be selected, and the author will have no idea why. Their static linter reports a clean file.

---

## Method

For each skill we take its `description` and a set of realistic user prompts, then compute what fraction of each prompt's content words appear in the description (after stopword removal and stemming).

- **fire coverage** — mean overlap with prompts the skill *should* answer. Higher is better.
- **nofire coverage** — mean overlap with adjacent prompts it should *ignore*. Lower is better.
- **margin** — the difference. This is the discriminating number: a long, generic description scores well on fire coverage simply by containing many words, but that also raises nofire coverage. Margin rewards descriptions that match their own job and not their neighbours'.

Prompts come from the skill's own `eval.yaml` where one exists, otherwise from the closest of [10 hand-written category suites](../eval-suites/). The category must clear an absolute floor **and** beat the runner-up by 1.3× — without that second test, a skill belonging to no category still gets assigned to whichever one it marginally resembles and is then judged against irrelevant prompts.

**Corpus:** 202 `SKILL.md` files sampled from six repositories (ponytail, anthropics/skills, obra/superpowers, vercel-labs/skills, alirezarezvani/claude-skills, jeremylongshore/claude-code-plugins-plus-skills). 77 had a confident prompt-set match and were analysed; 125 were skipped.

**Reproduce:** raw per-skill data at [docs/data/trigger-surface-2026-08.json](./data/trigger-surface-2026-08.json). Run it yourself with `doodle surface path/to/SKILL.md`.

---

## Results

### Coverage distribution

| Percentile | fire coverage |
| --- | ---: |
| p10 | 0.182 |
| p25 | 0.201 |
| p50 | 0.222 |
| p75 | 0.266 |
| p90 | 0.318 |
| **mean** | **0.239** |

Roughly a quarter of the vocabulary in a realistic request appears in the description meant to catch it. The distribution is tight — the gap between a p10 skill and a p90 skill is under 14 percentage points. Almost nobody is doing this well.

### Discrimination

| Metric | Value |
| --- | ---: |
| Median margin | −0.010 |
| Skills with margin ≤ 0 | **57%** |

A majority of skills match requests they should ignore *as well as or better than* the ones they exist to serve. This predicts over-firing — the failure mode where a skill activates on adjacent work and produces confidently irrelevant output. It is discussed far less than underfiring and appears to be at least as common.

### Length does not predict trigger quality

Correlation between description length and fire coverage: **r = +0.277** (n = 77), so length accounts for about **7.7%** of the variance.

This is the finding with the most direct consequence. Character-count limits are the most widely implemented rule in SKILL.md tooling. They are worth keeping — long descriptions waste context and dilute matching — but they are close to uninformative about whether a skill will actually be selected. A description can be trimmed to a perfect 240 characters and still share no vocabulary with its users.

### By repository

| Repo | Mean coverage | n |
| --- | ---: | ---: |
| DietrichGebert/ponytail | 0.280 | 1 |
| vercel-labs/skills | 0.280 | 1 |
| anthropics/skills | 0.275 | 10 |
| alirezarezvani/claude-skills | 0.253 | 28 |
| obra/superpowers | 0.218 | 5 |
| jeremylongshore/... | 0.215 | 32 |

Worth setting against the [static Quality Report](./QUALITY_REPORT.md), where obra/superpowers was the standout at 86% clean and anthropics/skills scored 6%. On trigger surface the ordering roughly inverts.

**Passing static lint and having a strong trigger surface are close to independent properties.** They are different questions, and only one of them determines whether the skill runs.

### The strongest and weakest

| | Skill | Coverage | Margin |
| --- | --- | ---: | ---: |
| Strongest | `ali/.gemini/skills/pr-review-expert` | 0.402 | +0.318 |
| | `ali/.gemini/skills/adversarial-reviewer` | 0.393 | +0.310 |
| | `anthropic/skills/skill-creator` | 0.371 | +0.065 |
| Weakest | `jeremy/.../hyperflow/skills/dispatch` | 0.153 | +0.014 |
| | `jeremy/.../clari-performance-tuning` | 0.160 | −0.007 |
| | `anthropic/skills/webapp-testing` | 0.182 | −0.027 |

The two strongest are both code-review skills whose descriptions read almost like the requests themselves. That is the whole technique: write the description in the user's words, not the implementer's.

---

## What to do about it

```bash
doodle surface path/to/SKILL.md
```

Output names the specific prompts your description fails to cover and the exact words it is missing:

```
  coverage of should-fire prompts   72%
  coverage of should-not-fire        0%
  margin                           +72%

  weakest should-fire matches:
     50%  look this diff over
          missing: look
     67%  review my staged changes
          missing: chang
```

The fix is usually to add three or four words. Not to rewrite anything.

If you keep an `eval.yaml` next to your `SKILL.md`, doodle uses your own prompts. Otherwise it picks the closest built-in category, or stays silent if none fits.

---

## Limitations

Stated plainly, because they matter for how much weight this deserves:

1. **Lexical overlap is a proxy.** Real skill selection uses embeddings, which capture semantic similarity that exact word matching misses. A description saying "inspect" and a user saying "review" will score 0 here and may well match in practice. The metric is a cheap offline screen, not ground truth.
2. **It is not yet validated empirically.** The obvious next study runs the same corpus through `doodle eval` — actually measuring firing rates against live prompts — and checks whether trigger surface predicts them. Until that is done, treat these numbers as a hypothesis with a plausible mechanism.
3. **Only 77 of 202 skills were analysable.** The 10 built-in categories cover common types; many published skills are niche integrations that fit none of them. Restricting to confidently-matched skills is the honest choice, but it means the sample skews toward mainstream categories.
4. **Category-matched prompts are not the author's prompts.** Where no `eval.yaml` existed, the skill was measured against prompts written for its category in general. A skill with an unusual but legitimate scope will score lower than it deserves.
5. **Snapshot in time.** Findings reflect the repository state when sampled.

---

## Follow-up

The validation study is the interesting one, and it is blocked only on API budget rather than on any design question. If you have credits and want to run it, the harness is `doodle eval` and the corpus is documented above — results welcome as a PR.

*If a rule here fires on your skill and you think it is wrong, that is worth an [issue](https://github.com/krishyaid-coder/doodle/issues). A metric that flags good descriptions is worse than no metric.*
