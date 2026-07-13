# Community eval-suite library

Category-specific `eval.yaml` templates for common skill types. Each template is a starting point — copy it, adapt the prompts to your specific skill, and run `doodle eval` to measure trigger accuracy.

## Why this exists

Phase 2 of doodle (`doodle eval`) measures whether Claude's automatic skill picker actually invokes your skill on natural-language prompts. Writing good `should_fire` and `should_not_fire` prompts from scratch is the hardest part of setting up an eval. This library gets you 80% of the way there.

## How to use

**Option A — CLI (recommended for new skills):**

```bash
doodle init my-reviewer --template=code-reviewer --eval
```

Scaffolds a category-tuned `SKILL.md` and copies the matching eval suite. From there, edit the prompts to match your specific tool and behaviors.

**Option B — Copy the eval.yaml directly (for existing skills):**

```bash
cp eval-suites/code-reviewer/eval.yaml your-skill/eval.yaml
```

Then edit the prompts.

## Available templates

| Template | For skills that... | Prompts |
| --- | --- | ---: |
| [`code-reviewer`](./code-reviewer/) | Review diffs, PRs, staged changes | 10 fire + 6 no-fire |
| [`refactorer`](./refactorer/) | Restructure code without changing behavior | 10 fire + 6 no-fire |
| [`sql-generator`](./sql-generator/) | Write SQL queries from natural-language questions | 10 fire + 6 no-fire |
| [`docs-writer`](./docs-writer/) | Write README, API docs, technical explanations | 10 fire + 6 no-fire |
| [`test-writer`](./test-writer/) | Author unit, integration, or e2e tests | 10 fire + 6 no-fire |
| [`security-auditor`](./security-auditor/) | Check code for CVEs, OWASP issues, injection risks | 10 fire + 6 no-fire |
| [`debugger`](./debugger/) | Investigate errors, stack traces, root causes | 10 fire + 6 no-fire |
| [`data-engineer`](./data-engineer/) | Design pipelines, ETL, dbt models, Airflow DAGs | 10 fire + 6 no-fire |
| [`api-designer`](./api-designer/) | Design REST/GraphQL schemas and endpoints | 10 fire + 6 no-fire |
| [`skill-creator`](./skill-creator/) | Author or improve Claude skills | 10 fire + 6 no-fire |

## Contributing a new template

New categories are welcome. See [CONTRIBUTING to eval-suites](#contributing-to-eval-suites) below.

### Guidelines

1. **10 should_fire prompts.** Vary phrasing (formal/casual, verb/noun, short/long). Include at least one non-obvious way a real user would ask.
2. **5–6 should_not_fire prompts.** These are the hard ones. Pick adjacent categories that sound similar but are a different skill's job.
3. **Follow the convention.** Each template lives at `eval-suites/<name>/{eval.yaml,notes.md}`.
4. **notes.md explains scope.** Two paragraphs: what the category is, and one concrete example of adaptation.
5. **Test your template.** Every included template has been checked to pass `doodle` linting on the generated SKILL.md.

### Contributing to eval-suites

Fork, add a directory under `eval-suites/`, open a PR with the two files and a matching entry in the table above. Include a one-line description of the category's scope and why the `should_not_fire` prompts you chose are non-trivial.
