# debugger eval suite

## Scope

Skills that investigate errors, crashes, wrong outputs, or unexpected behavior. Diagnosis, not repair. If your skill both diagnoses and fixes, split into two eval suites or combine with the `refactorer` template.

## Why the should_not_fire prompts are tricky

- **Fixing ≠ debugging.** "Fix this bug" is a different intent — the user has already skipped the diagnosis step.
- **Understanding ≠ debugging.** "Explain how this library works" is learning, not root-cause analysis.
- **Instrumentation ≠ debugging.** Adding log statements is prep, not investigation.
- **Profiling ≠ debugging.** Perf work looks at where time is spent, not why output is wrong.

## Adapting for your specific tool

- **Language-scoped** — Python stack traces vs JavaScript vs Rust vs JVM have different vocabularies.
- **Runtime-scoped** — production incident debugging vs local dev debugging need different `should_not_fire` (in prod, "fix this" often IS the intent; locally it usually isn't).
- **Domain-scoped** — a database-query debugger is a different skill from a distributed-systems debugger.
