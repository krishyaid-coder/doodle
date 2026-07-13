# docs-writer eval suite

## Scope

Skills that produce technical documentation: READMEs, API references, docstrings, guides, tutorials. New writing, not editing or translation of existing writing.

## Why the should_not_fire prompts are tricky

- **Editing vs writing.** "Shorten this" or "review my docs" is editing.
- **Translation ≠ authoring.** Translating existing docs is a language-transformation task.
- **Marketing copy vs technical docs.** Landing pages, ad copy, and press releases share vocabulary with docs but need different tone and structure.
- **Build orchestration ≠ writing.** "Run the docs build" is CI, not authoring.

## Adapting for your specific tool

- **Format-scoped** — Markdown vs Sphinx vs docstrings vs OpenAPI. Narrow the `should_fire` to your target format.
- **Audience-scoped** — end-user tutorials vs internal engineering docs vs API reference. Different audiences need different prompts.
- **Tone-scoped** — if your skill enforces a specific voice (Anthropic, Stripe, Google's technical writing style), consider adding a prompt like `"in the ACME house style"` to positive examples.
