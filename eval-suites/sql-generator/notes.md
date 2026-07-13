# sql-generator eval suite

## Scope

Skills that take a natural-language analytics or business question and produce a SQL query. Read-side only — SELECTs, aggregations, joins, window functions. Not schema design, not query optimization, not code review of hand-written SQL.

## Why the should_not_fire prompts are tricky

- **Query optimization is a different skill.** It reads an existing query and improves it, not "here is a question, produce a query."
- **Schema design is a different skill.** It designs DDL, not DML.
- **SQL review is a different skill.** Reads a written query for issues.
- **Language translation** (SQL → Pandas or vice versa) is transformation, not generation.

## Adapting for your specific tool

- **Dialect-scoped** — add `"write Postgres 15 SQL for..."` or `"Snowflake query for..."` and gate on the dialect keyword.
- **Read-only vs mutation-capable** — if your skill can also emit INSERT/UPDATE/DELETE, add matching prompts. Otherwise add `"insert a row..."` to `should_not_fire`.
- **BI-focused** — if your skill is opinionated about semantic layers (dbt, Cube, Lightdash), add positive prompts using those terms.
