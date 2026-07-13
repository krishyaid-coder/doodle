# data-engineer eval suite

## Scope

Skills that design data infrastructure: ETL/ELT pipelines, dbt models, Airflow DAGs, Kafka topic layouts, data warehouse schemas. Design and structure, not one-off queries and not application backends.

## Why the should_not_fire prompts are tricky

- **SQL query ≠ pipeline.** "Write a query to..." belongs to `sql-generator`.
- **Reviewing a DAG ≠ designing one.** Different mode.
- **Running the build ≠ designing.** Orchestration is different.
- **Application backend ≠ data infrastructure.** Both design systems but with different concerns.

## Adapting for your specific tool

- **Warehouse-scoped** — Snowflake vs BigQuery vs Postgres data warehouse vs Databricks lakehouse. Design idioms differ.
- **Framework-scoped** — dbt-first vs Airflow-first vs Prefect-first shapes the vocabulary heavily.
- **Batch vs streaming** — real-time (Kafka, Flink, Spark Streaming) is a different design surface than batch. Consider whether one skill covers both.
