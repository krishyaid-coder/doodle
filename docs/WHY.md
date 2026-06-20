# Why doodle exists

> A short, honest answer to: *"is this just another open-source project, or does it actually move something?"*

---

## The shape of the problem

In late 2025, Anthropic shipped a new format for extending Claude: `SKILL.md`. A markdown file with YAML frontmatter. By mid-2026 there are **5,000+ published skills** across community marketplaces.

Three things are true at once:

1. **Authoring is harder than it looks.** Anthropic's own issue tracker quantifies the failure modes: [`anthropics/skills#267`](https://github.com/anthropics/skills/issues/267) attributes **80%** of trigger failures to vague descriptions, **60%** to missing keywords, **30%** to conflicting triggers.
2. **Most skills in the wild don't follow the rules.** We sampled 19 published `SKILL.md` files from the most-starred community repos (ponytail at 33k ⭐, alirezarezvani/claude-skills at 5.2k ⭐, jeremylongshore's 2.8k-skill pack). Roughly **40–60%** have at least one clear quality smell: a 770-character description, a 1,247-line body, hardcoded `/Users/` paths, emoji in places the style guide discourages.
3. **There is no quality bar.** Marketplaces accept submissions without checks. Anthropic's docs link to no community tooling. Authors have no way to know if their skill will actually fire before they ship it.

doodle is the smallest useful step in front of that gap.

---

## What success looks like (and how we'd measure it)

We aren't building a linter "because there should be one." We're building it because three concrete outcomes are reachable and measurable:

| Outcome | Signal we'd watch for | Why it matters |
|---|---|---|
| Authors fix issues we surface | Pull requests on community skills citing a doodle rule ID | The rule-set is delivering real change, not vibes |
| Marketplaces adopt it as a submission gate | Public configs / CI workflows running `doodle --strict` | Quality bar moves once, ecosystem-wide |
| Anthropic links it from docs | A reference in the agent-skills authoring page | Distribution + endorsement; the cleanest legitimacy path |

If none of these happen in six months, the project failed and we should say so out loud.

---

## What makes this different from a generic prompt-linter

This is the question we keep coming back to. Honest version:

- **It's grounded in real data, not vibes.** Every v0 rule has an in-sample frequency from 19 published skills. The vague-trigger blocklist is sourced from the exact phrases Anthropic flagged in `#267`. Rules with zero in-sample frequency stayed in the deferred list.
- **It respects the dialect split.** Anthropic-style minimal frontmatter and the community-extended schema diverge in the wild. A linter that ignores that is preachy and gets uninstalled.
- **It has a path to trigger-accuracy.** Static checks alone don't catch the most important class of bugs — "this skill never fires." [Promptfoo](https://www.promptfoo.dev/docs/guides/test-agent-skills/) ships a `skill-used` assertion. Our Phase 2 wraps it. Nobody else has put these two halves together.
- **It's small enough to read in an afternoon.** Twelve rules, six source files, two runtime deps. The entire architecture is in [ARCHITECTURE.md](./ARCHITECTURE.md). Contribution friction is low.

---

## What it explicitly does *not* try to be

- **Not a competitor to skill-creator.** Anthropic's first-party tool generates scaffolding. doodle grades the result. They compose; they don't compete.
- **Not an evaluation framework.** Promptfoo does that better than we ever will. We integrate, we don't reinvent.
- **Not a vibes-based "AI tool".** No LLM calls in the lint path. Determinism is the product. You should get the same findings on the same file forever.

---

## The honest risk

Anthropic could ship an official skill linter tomorrow and obsolete this. We accept that.

The bet is that even if they do:

- We'll have shipped first and built the rule-set authors trust.
- The trigger-accuracy harness (Phase 2) is the harder, more valuable half — and the half Anthropic is least likely to build, because it's adjacent to their model behavior they're already trying to *not* externally benchmark.
- The hosted scanner (Phase 3) is a product, not a feature. Different motion.

If we're wrong and Anthropic absorbs the whole space, the rule-set lives on as a contribution to their canonical tool. That's still a good outcome.

---

## Who this is for

In rough order of who benefits most today:

1. **Skill authors with a `SKILL.md` they're about to publish.** One command, actionable findings, no LLM bill.
2. **Marketplace operators** who need a quality gate without staffing reviewers.
3. **Teams shipping internal Claude Code skills** who want CI guardrails before code review.
4. **Anthropic itself**, if they want a community-grown reference for what "good" looks like.

---

## What "real impact" actually requires

A linter is not impact. Adopted rules are impact. So:

- Every rule needs a citation a human can argue with.
- Every false positive costs trust. We err toward `warning` over `error`.
- The launch isn't "we built a thing." It's "we linted ponytail and the top 20 marketplace skills and here's the report." Specific. Concrete. Useful before any install.

If you read this and disagree, [open an issue](https://github.com/krishyaid-coder/doodle/issues). The project gets better when authors push back on rules. That's the whole point.
