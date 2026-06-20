# Contributing

Thanks for considering a contribution. doodle is small on purpose, but it grows by community signal with new rules, fixture skills, dialects, formatters.

## Quick links

- **Add a rule:** [docs/EXTENDING.md](./docs/EXTENDING.md)
- **Architecture overview:** [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- **Rule spec:** [RULES.md](./RULES.md)
- **Why this exists:** [docs/WHY.md](./docs/WHY.md)

## Ground rules

1. **Open an issue before a large PR.** Especially for new rules, I want to discuss the citation and false-positive risk together.
2. **Every rule needs a citation.** Anthropic docs, a community issue, or a sample frequency. No "I think this is bad."
3. **Tests required.** A rule PR without a fixture + a test will be asked to add them.
4. **Severity is conservative.** `warning` is the default. `error` is for "the skill will not load or trigger."
5. **Be kind in suggestions.** Authors read these messages on their work. "Trim to 250 chars" beats "your description is bloated."

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Pull request checklist

- [ ] Tests pass (`pytest`)
- [ ] New rule? Added fixture + test + entry in [RULES.md](./RULES.md)
- [ ] Public-facing change? README / docs updated
- [ ] Commit messages describe the *why*

## Code of conduct

Be excellent. Disagreements about rules are healthy. Disagreements about people are not.
