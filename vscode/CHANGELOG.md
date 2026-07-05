# Changelog

## 0.2.0 — marketplace launch

- **Status bar item** showing finding count on the active `SKILL.md` (`$(error)/$(warning)/$(check)` icons). Click to reveal the output channel.
- **`doodle: Run trigger-accuracy eval (Phase 2)` command** — runs `doodle eval` on the current file and streams the report into a persistent output channel. Requires `promptfoo` + `ANTHROPIC_API_KEY`.
- **`doodle: Show output channel` command** — reveals the shared doodle output channel.
- **`doodle.showStatusBar` setting** — hide the status bar item if you'd rather.
- **Icon added** — the doodle mascot, cropped square. Renders in the marketplace listing.
- Small cleanups: shared output channel across explain/eval, cleaner disposal on deactivate.

## 0.1.0 — initial release

- Real-time linting of `SKILL.md` files via the open-source [doodle](https://github.com/krishyaid-coder/doodle) CLI
- Diagnostics with rule ID, message, suggestion, and a clickable link to the rule docs
- Quick-fix code action for fixable rules (`hygiene/desc-blank-lines`, `body/emoji`)
- Commands: lint current file, apply auto-fixes, explain rule
- Configurable trigger mode (save / change / open), debounce, strict mode, custom config path
