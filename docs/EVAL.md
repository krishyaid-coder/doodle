<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/logo-wordmark-dark.svg">
    <img src="./assets/logo-wordmark-light.svg" alt="doodle" width="240"/>
  </picture>
</p>

# `doodle eval` — trigger-accuracy harness

Phase 1 (`doodle lint`) asks: **does your skill *look* right?**
Phase 2 (`doodle eval`) asks: **does your skill *actually work*?**

A skill can pass every static rule and still never fire when users phrase their request naturally. Per Anthropic's own issue tracker, 80% of trigger failures fall into this category. The only way to know is to test it against real prompts.

`doodle eval` wraps [Promptfoo's `skill-used` assertion](https://www.promptfoo.dev/docs/guides/test-agent-skills/), so we don't reinvent the eval runtime — we generate the right config, run it, and score the result.

---

## Install

```bash
pip install "doodle-lint[eval]"      # adds the anthropic SDK
npm install -g promptfoo             # the eval runtime
export ANTHROPIC_API_KEY=sk-...      # needed for --generate and for promptfoo runs
```

---

## The 5-minute workflow

```text
1. Write SKILL.md
       │
       ▼
2. doodle lint SKILL.md           ◄── fix obvious static issues
       │
       ▼
3. doodle eval --generate SKILL.md   ◄── Claude drafts 10+10 starter prompts
       │  edit eval.yaml to keep / remove / add
       ▼
4. doodle eval SKILL.md           ◄── runs prompts, reports score
       │  iterate description until accuracy is high
       ▼
5. Ship + add to CI
```

---

## `eval.yaml` schema

`eval.yaml` sits next to `SKILL.md`. It defines the contract: which prompts should trigger your skill, which shouldn't.

```yaml
model: claude-sonnet-4-5

should_fire:
  - "review my staged changes"
  - "security pass before I commit"
  - "look this diff over"

should_not_fire:
  - "write me a new function"
  - "explain what this code does"
  - "what's the weather"
```

That's the whole format.

---

## Commands

### Generate a starter `eval.yaml`

```bash
doodle eval --generate path/to/SKILL.md
# writes eval.yaml next to the SKILL.md
```

Claude reads your description and proposes 10 `should_fire` + 10 `should_not_fire` prompts. **Treat the output as a draft** — review every line, delete what's wrong, add what's missing.

Preview the prompt that would be sent without spending tokens:

```bash
doodle eval --generate path/to/SKILL.md --dry-run
```

### Run the eval

```bash
doodle eval path/to/SKILL.md
```

Output:

```
path/to/SKILL.md
  should_fire     2/3  (67%)
  should_not_fire 2/2  (100%)
  overall         4/5  (80%)

  Misses (expected fire, didn't):
    - 'look this diff over'
```

The misses tell you exactly what to fix in your description.

Preview the Promptfoo config that would run, without invoking it:

```bash
doodle eval path/to/SKILL.md --dry-run
```

---

## Use in CI

Add as a separate step after lint. Use a low-frequency trigger (nightly, or on release branches) since each run costs API tokens.

```yaml
- name: doodle eval
  if: github.event_name == 'schedule'
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    pip install "doodle-lint[eval]"
    npm install -g promptfoo
    doodle eval ./skills/critical-skill/
```

`doodle eval` exits `0` when all prompts behave as expected, `1` if any are wrong, `3` on tool errors. Block merges on regressions by gating on the exit code.

---

## Tips

- **Start small.** 5 + 5 prompts beats 20 + 20 if the 5+5 are sharp.
- **The "almost but not quite" prompts are the highest-leverage half.** Most authors write only `should_fire`. The `should_not_fire` list is what prevents over-firing.
- **Iterate the description, not the prompts.** If a should-fire prompt misses, the fix is usually a clearer description, not a different prompt.
- **Add to eval.yaml when users report issues.** Every "why didn't your skill fire on X" becomes a test case.

---

## Internals (1-paragraph version)

`doodle eval` generates a Promptfoo config from your `eval.yaml`, shells out to `promptfoo eval --output json`, parses the result back into a score. We don't reimplement Promptfoo — we generate its input and consume its output. If Promptfoo's `skill-used` assertion schema changes, the only file that needs updating is [`src/doodle/eval/promptfoo.py`](../src/doodle/eval/promptfoo.py).

---

## Why this matters

A linter is half the story. The trigger-accuracy half is what separates a skill that ships at 95% reliability from one that ships at 30% and quietly never fires.

If you operate a Claude skills marketplace, requiring `eval.yaml` + a minimum score is the cleanest quality bar you can put in place.
