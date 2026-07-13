# test-writer eval suite

## Scope

Skills that author new tests: unit, integration, e2e, TDD. Not test running, not test analysis, not conversion between frameworks.

## Why the should_not_fire prompts are tricky

- **Debugging a failing test ≠ writing tests.** "Why is this failing?" is investigation.
- **Test framework migration ≠ authoring.** "Convert mocha to jest" is transformation.
- **Coverage analysis ≠ authoring.** "Improve the coverage report" is measurement.
- **Test data ≠ tests.** "Generate a mock fixture" is data, not a test file.

## Adapting for your specific tool

- **Language-scoped** — narrow to pytest, jest, JUnit, RSpec, etc. Add matching positive prompts and move other-language prompts to `should_not_fire`.
- **Type-scoped** — if your skill only writes unit tests, remove integration/e2e prompts. If e2e-only, do the opposite.
- **Framework-adjacent** — Playwright, Cypress, Selenium; consider whether these are the same skill or three.
