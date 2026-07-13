# code-reviewer eval suite

## Scope

Skills that review already-written code — diffs, staged changes, pull requests, or specific files — for correctness, style, security, or maintainability. This is the "second set of eyes" role, not the authoring role.

## Why the should_not_fire prompts are tricky

The main confusions to guard against:

- **Analysis ≠ review.** "Explain what this code does" wants an explanation, not a judgment. Different skill.
- **Formatting ≠ review.** "Prettify this" is a formatter's job, even though it involves reading code.
- **Testing ≠ review.** "Run the tests" is orchestration, not review.
- **Authoring ≠ review.** "Write a new function" is creation.

If your skill also authors code or runs tests, adapt the suite: move the relevant prompts from `should_not_fire` to `should_fire`, or split into two skills.

## Adapting for your specific tool

Common variations:

- **Security-focused reviewer** — add prompts like `"CVE audit on my dependencies"`, `"OWASP scan on this diff"`. Consider whether you want overlap with the `security-auditor` category or a clear separation.
- **Language-specific reviewer** — add `"review my Python for PEP 8 issues"` or `"lint my TypeScript"`. Add matching `should_not_fire` prompts for other languages.
- **Team-policy reviewer** — add `"check the ACME code standards"` or your internal policy keyword.
