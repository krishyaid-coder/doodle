# doodle for VS Code

Real-time lint feedback for [Claude `SKILL.md` files](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices). The extension surfaces the same findings you would get from running the [`doodle`](https://github.com/krishyaid-coder/doodle) command-line tool, inline as you author.

Published on the [Open VSX Registry](https://open-vsx.org/extension/krishyaid-coder/doodle-lint). Works in Cursor, VSCodium, Windsurf, and VS Code with Open VSX enabled.

## Features

- Diagnostics on every line with a quality issue, matching the CLI's rule set and severity tiers.
- Hover messages containing the rule ID, actionable suggestion, and a clickable link to the [rule catalog](https://github.com/krishyaid-coder/doodle/blob/main/RULES.md).
- Quick-fix code actions for fixable rules (`hygiene/desc-blank-lines`, `body/emoji`).
- Status bar item on the active `SKILL.md` showing error, warning, and info counts.
- Bridge command for `doodle eval`, the Phase 2 trigger-accuracy harness.
- Configurable trigger (save, change, or open), debounce interval, virtualenv path, and `.doodle.toml` location.

## Prerequisites

The extension shells out to the `doodle` CLI. Install it separately:

```bash
pip install git+https://github.com/krishyaid-coder/doodle.git
```

Verify:

```bash
doodle --version
```

If `doodle` is installed inside a project virtualenv rather than on the global `PATH`, point the extension at the binary explicitly in VS Code settings:

```json
"doodle.command": "/absolute/path/to/.venv/bin/doodle"
```

## Install

From your editor's Extensions panel, search `doodle` and click Install.

From the command line:

```bash
# Cursor, VSCodium, Windsurf (Open VSX is the default gallery)
code --install-extension krishyaid-coder.doodle-lint

# Vanilla VS Code: install the VSIX attached to the latest GitHub Release
curl -L -o /tmp/doodle.vsix \
  https://github.com/krishyaid-coder/doodle/releases/latest/download/doodle-lint-0.2.0.vsix
code --install-extension /tmp/doodle.vsix
```

## Commands

Available in the Command Palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` elsewhere):

| Command                                       | Behavior                                                                                       |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `doodle: Lint current SKILL.md`               | Force a re-lint of the active file                                                             |
| `doodle: Apply auto-fixes to current SKILL.md`| Runs `doodle --fix` on the active file and re-lints                                            |
| `doodle: Explain a rule`                      | Prompts for a rule ID and prints its metadata to the output channel                            |
| `doodle: Run trigger-accuracy eval (Phase 2)` | Runs `doodle eval` on the active file. Requires `promptfoo` on `PATH` and `ANTHROPIC_API_KEY`. |
| `doodle: Show output channel`                 | Reveals the shared doodle output channel                                                       |

## Settings

| Setting               | Default  | Description                                                                                     |
| --------------------- | -------- | ----------------------------------------------------------------------------------------------- |
| `doodle.command`      | `doodle` | Path to the CLI. Absolute path required for virtualenv installs.                                |
| `doodle.strict`       | `false`  | Run with `--strict`, promoting info to warning and warning to error.                            |
| `doodle.runOn`        | `save`   | When to lint. Options: `save`, `change` (debounced), `open`.                                    |
| `doodle.debounceMs`   | `400`    | Debounce interval in milliseconds when `runOn` is `change`.                                     |
| `doodle.configFile`   | `""`     | Path to a `.doodle.toml`. Empty means auto-discover by walking up the directory tree.           |
| `doodle.showStatusBar`| `true`   | Show the finding-count status bar item on `SKILL.md` files.                                     |

## Design

The extension is roughly 250 lines of TypeScript. On a `SKILL.md` change it spawns `doodle <path> --format=json --no-color`, parses the output, and converts each finding into a `vscode.Diagnostic`. Fixable rules are surfaced as `CodeActionKind.QuickFix` actions that invoke the `doodle.fixCurrentFile` command.

Because all lint logic lives in the Python CLI, upgrading the CLI upgrades the extension's rules. No extension republish is required for new rules, revised messages, or changed severities.

Source: [github.com/krishyaid-coder/doodle/tree/main/vscode](https://github.com/krishyaid-coder/doodle/tree/main/vscode).

## Non-goals

- The extension does not lint files that are not named `SKILL.md`.
- The extension does not bundle the Python runtime. Users install and control their own version of the CLI.
- The extension does not implement rule logic. That belongs in the CLI so it stays testable in isolation.

## Issues and contributions

Bug reports and rule suggestions: [github.com/krishyaid-coder/doodle/issues](https://github.com/krishyaid-coder/doodle/issues).

## License

MIT.
