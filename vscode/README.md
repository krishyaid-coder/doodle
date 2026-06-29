# doodle — Claude SKILL.md linter (VS Code extension)

Real-time lint feedback for [Claude `SKILL.md` files](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices). Catches the vague descriptions, oversized bodies, hardcoded paths, and silent trigger failures that keep skills from firing — as you author.

Wraps the open-source [`doodle`](https://github.com/krishyaid-coder/doodle) CLI.

---

## What you get

- 🟡 **Squiggly underlines** on every line with a quality issue
- 🛈 **Hover messages** with the rule ID, the actionable suggestion, and a link to the [rule catalog](https://github.com/krishyaid-coder/doodle/blob/main/RULES.md)
- 🔧 **Quick-fix code action** for fixable rules (blank-line description, emoji)
- 📋 **Command palette**: `doodle: Lint current SKILL.md`, `doodle: Apply auto-fixes`, `doodle: Explain a rule`
- ⚙️ **Configurable**: choose when to lint (save / change / open), point at a virtualenv, force strict mode, supply a `.doodle.toml`

---

## Prerequisites

You need the `doodle` CLI installed and reachable. The extension shells out to it — it doesn't bundle Python.

```bash
pip install doodle-lint
```

Verify:

```bash
doodle --version
# doodle 0.4.0
```

If `doodle` isn't on PATH (e.g. you installed it into a project venv), set `doodle.command` in VS Code settings to the absolute path of the binary, e.g. `/Users/me/project/.venv/bin/doodle`.

---

## Settings

| Setting | Default | Description |
|---|---|---|
| `doodle.command` | `doodle` | Path to the CLI. Use an absolute path for venvs. |
| `doodle.strict` | `false` | Run with `--strict` (promotes info → warning, warning → error). |
| `doodle.runOn` | `save` | When to lint: `save`, `change` (debounced), `open`. |
| `doodle.debounceMs` | `400` | Debounce when `runOn = change`. |
| `doodle.configFile` | `""` | Path to a `.doodle.toml`. Empty means auto-discover up the tree. |

---

## Commands

Reach via Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`):

- **doodle: Lint current SKILL.md** — force a re-lint of the active file
- **doodle: Apply auto-fixes to current SKILL.md** — runs `doodle --fix` and re-lints
- **doodle: Explain a rule** — pops up a rule ID prompt; shows the rule's metadata + citation in an output channel

---

## How it works

The extension is intentionally minimal: ~150 lines of TypeScript. On a `SKILL.md` change, it spawns `doodle <path> --format=json --no-color`, parses the output, and converts each finding into a VS Code diagnostic.

Because the lint logic lives in the Python CLI, you always get the rules your installed version provides. Upgrade `doodle-lint` in your venv and the extension picks it up immediately — no extension republish needed.

Code: [github.com/krishyaid-coder/doodle/tree/main/vscode](https://github.com/krishyaid-coder/doodle/tree/main/vscode)

---

## What this extension does not (yet) do

- Run Phase 2 trigger-accuracy evals (use `doodle eval` from the CLI for that — it needs an API key and Promptfoo)
- Lint files that aren't named `SKILL.md`
- Bundle the Python runtime (deliberate — keeps the extension < 100 KB and lets you control the version)

---

## Issues + contributions

Bug reports and rule suggestions: [github.com/krishyaid-coder/doodle/issues](https://github.com/krishyaid-coder/doodle/issues)

---

## License

MIT. Same as the doodle CLI.
