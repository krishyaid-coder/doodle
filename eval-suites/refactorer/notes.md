# refactorer eval suite

## Scope

Skills that restructure existing code without changing observable behavior. Extract-function, rename, simplify, deduplicate, split-file. Not performance work, not rewrites, not adding features.

## Why the should_not_fire prompts are tricky

- **Optimization ≠ refactoring.** Perf work often changes behavior at the boundary (memory, latency). Different skill.
- **Rewriting ≠ refactoring.** "Write a new implementation" implies discarding, not restructuring.
- **Reviewing ≠ refactoring.** Review reports issues; refactor changes code.
- **Porting ≠ refactoring.** Cross-language work is a migration, not a refactor.

## Adapting for your specific tool

- **Language-scoped refactorer** — add positive prompts naming the language and a negative prompt for other languages.
- **Framework-specific** — e.g. "React hooks refactor" or "Django ORM cleanup" — narrow both fire and no-fire lists.
- **Automated vs interactive** — if your skill only does one refactoring pattern (e.g. rename-only), remove the broader `"clean up this code"` prompts.
