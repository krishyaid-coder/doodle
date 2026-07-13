# skill-creator eval suite

## Scope

Skills that help users author *other* Claude skills — writing the SKILL.md, tuning descriptions for trigger fidelity, drafting eval.yaml suites. Meta-tooling, not a runtime.

## Why the should_not_fire prompts are tricky

- **Explaining ≠ authoring.** "Explain what a Claude skill is" is education.
- **Running ≠ authoring.** "Run my skill" is invocation.
- **Reviewing ≠ authoring.** "Review my SKILL.md" belongs to a `code-reviewer` or `docs-writer` style skill.
- **Package management ≠ authoring.** Install/list operations are runtime metadata.

## Adapting for your specific tool

- **Doodle-specific** — if your skill wraps or extends doodle (rule authoring, custom configs), narrow prompts around that.
- **Category-focused** — a skill-creator specialized for security-review-skills is different from a generic one.
- **Marketplace-focused** — an authoring assistant that also handles publishing is a broader skill than a pure authoring one.
