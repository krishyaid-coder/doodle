# Changelog

## 0.1.0 — initial release

- Real-time linting of `SKILL.md` files via the open-source [doodle](https://github.com/krishyaid-coder/doodle) CLI
- Diagnostics with rule ID, message, suggestion, and a clickable link to the rule docs
- Quick-fix code action for fixable rules (`hygiene/desc-blank-lines`, `body/emoji`)
- Commands: lint current file, apply auto-fixes, explain rule
- Configurable trigger mode (save / change / open), debounce, strict mode, custom config path
