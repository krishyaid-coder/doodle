"""Category-specific starter templates for ``doodle init --template <name>``.

Each template pairs a tuned SKILL.md description (that passes the linter with
zero warnings) with a matching ``should_fire`` / ``should_not_fire`` eval
suite. Templates are embedded in Python rather than read from ``eval-suites/``
so the CLI works regardless of install shape (editable, wheel, PyPI).

The on-disk ``eval-suites/`` directory is the browsable community-facing
reference; ``tests/test_templates.py`` guards that the embedded prompt lists
here stay in sync with the yaml files there.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Template:
    """A starter template for ``doodle init``.

    Attributes:
        name: kebab-case identifier used with ``--template``.
        description: goes into the SKILL.md frontmatter ``description`` field.
                     Tuned to pass the linter (under 250 chars, contains an
                     explicit trigger phrase, no vague-trigger overlap).
        summary: one-line description shown in ``--list-templates``.
        should_fire: user prompts where Claude SHOULD invoke this skill.
        should_not_fire: adjacent-but-different prompts that should NOT trigger.
    """

    name: str
    description: str
    summary: str
    should_fire: tuple[str, ...]
    should_not_fire: tuple[str, ...]


CODE_REVIEWER = Template(
    name="code-reviewer",
    description=(
        "Inspects diffs for correctness, security, and portability. Use when "
        "the user says 'review my changes' or wants a check before committing."
    ),
    summary="Reviews diffs and pull requests for correctness and security.",
    should_fire=(
        "review my staged changes",
        "look at this diff before I commit",
        "security pass on this pull request",
        "audit my PR before I open it",
        "check the changes I'm about to push",
        "review this patch",
        "spot-check my code changes",
        "walk through my staged diff",
        "look for issues in what I'm about to commit",
        "review before I merge to main",
    ),
    should_not_fire=(
        "write me a new function",
        "explain what this code does",
        "format this file with prettier",
        "help me understand this codebase",
        "run the tests",
        "generate documentation for this module",
    ),
)


REFACTORER = Template(
    name="refactorer",
    description=(
        "Restructures code without changing observable behavior. Use when the "
        "user says 'refactor this', 'simplify this class', or 'reduce duplication'."
    ),
    summary="Restructures code without changing observable behavior.",
    should_fire=(
        "refactor this function",
        "simplify this class",
        "extract this into a helper function",
        "reduce the duplication in this file",
        "clean up this code without changing behavior",
        "restructure this module for clarity",
        "break this up into smaller pieces",
        "improve the design of this without changing what it does",
        "make this more maintainable",
        "tidy up this implementation",
    ),
    should_not_fire=(
        "review my code for bugs",
        "write a new implementation of this",
        "explain how this works",
        "add tests for this function",
        "optimize this for performance",
        "port this to another language",
    ),
)


SQL_GENERATOR = Template(
    name="sql-generator",
    description=(
        "Writes SQL from natural-language analytics questions. Use when the "
        "user says 'query for', 'write SQL to', or asks for a SELECT for a "
        "business question."
    ),
    summary="Writes SQL from natural-language analytics questions.",
    should_fire=(
        "write a query to find users who signed up last week",
        "generate SQL for top 10 products by revenue",
        "SQL for the number of orders grouped by month",
        "give me a query to join orders and customers on the customer id",
        "produce a SELECT that returns active accounts with more than 5 events",
        "write SQL to compute the 90th percentile order value",
        "query for churned users in the last 30 days",
        "SQL to find duplicate email addresses in the users table",
        "write the query for the KPI dashboard",
        "generate a SQL statement for this reporting question",
    ),
    should_not_fire=(
        "review the SQL I wrote",
        "explain what this query does",
        "optimize this SQL for a large table",
        "convert this SQL to Pandas",
        "help me design a database schema",
        "run this query against production",
    ),
)


DOCS_WRITER = Template(
    name="docs-writer",
    description=(
        "Produces technical documentation like READMEs, API references, and "
        "docstrings. Use when the user says 'write docs for', 'document this "
        "API', or 'add docstrings'."
    ),
    summary="Produces READMEs, API references, and docstrings.",
    should_fire=(
        "write a README for this project",
        "document this API endpoint",
        "add docstrings to these functions",
        "produce reference documentation for this library",
        "write a getting-started guide",
        "draft the installation section for the README",
        "explain how to use this SDK in a doc",
        "add JSDoc comments to this module",
        "write user-facing documentation for this feature",
        "generate a CONTRIBUTING guide for this repo",
    ),
    should_not_fire=(
        "review my documentation",
        "translate this README to Spanish",
        "shorten this README to fit in 500 characters",
        "run the docs build",
        "check that the code examples in my docs still work",
        "generate a marketing landing page",
    ),
)


TEST_WRITER = Template(
    name="test-writer",
    description=(
        "Authors unit, integration, and end-to-end tests. Use when the user "
        "says 'write tests for', 'add coverage', or wants to TDD a feature."
    ),
    summary="Authors unit, integration, and end-to-end tests.",
    should_fire=(
        "write unit tests for this function",
        "add pytest tests for the error cases",
        "generate integration tests for this API endpoint",
        "TDD this feature",
        "cover the edge cases with tests",
        "write jest tests for this component",
        "add coverage for the exception paths",
        "test the happy path and one failure mode",
        "generate table-driven tests for these inputs",
        "write regression tests for this bug",
    ),
    should_not_fire=(
        "review the tests I wrote",
        "run the test suite",
        "explain why this test is failing",
        "improve the coverage report",
        "generate a mock fixture for this data",
        "convert my mocha tests to jest",
    ),
)


SECURITY_AUDITOR = Template(
    name="security-auditor",
    description=(
        "Audits code for OWASP vulnerabilities, injection risks, and "
        "hardcoded secrets. Use when the user says 'security pass on this' "
        "or 'check for CVEs'."
    ),
    summary="Audits code for OWASP issues, injection risks, and CVEs.",
    should_fire=(
        "check this code for security issues",
        "audit this for OWASP top 10 concerns",
        "look for SQL injection risks in these queries",
        "scan this dependency list for CVEs",
        "review this for XSS vulnerabilities",
        "check for hardcoded secrets in this file",
        "audit the auth flow for security issues",
        "look at this for common web-security mistakes",
        "spot potential command injection here",
        "security review before I ship",
    ),
    should_not_fire=(
        "review my code for bugs",
        "explain what SQL injection is",
        "write a new authentication system",
        "generate a security policy document",
        "check my code style",
        "run the linter",
    ),
)


DEBUGGER = Template(
    name="debugger",
    description=(
        "Investigates errors, crashes, and unexpected behavior to find root "
        "causes. Use when the user says 'why is this failing' or 'debug this "
        "error'."
    ),
    summary="Investigates errors and finds root causes.",
    should_fire=(
        "help me debug this error",
        "why is this failing",
        "walk through this stack trace",
        "find the root cause of this bug",
        "investigate why this test is failing",
        "trace through this crash",
        "explain why this exception is being raised",
        "what's causing this timeout",
        "debug this weird behavior",
        "help me figure out why the output is wrong",
    ),
    should_not_fire=(
        "fix this bug for me",
        "write me a new implementation",
        "review my code",
        "explain how this library works",
        "write logging statements for this function",
        "profile this for performance",
    ),
)


DATA_ENGINEER = Template(
    name="data-engineer",
    description=(
        "Designs ETL pipelines, dbt models, and Airflow DAGs. Use when the "
        "user says 'design a pipeline', 'sketch a DAG', or asks for data "
        "infrastructure."
    ),
    summary="Designs ETL pipelines, dbt models, and Airflow DAGs.",
    should_fire=(
        "design an ETL pipeline for this data source",
        "create an Airflow DAG for the ingestion job",
        "build a dbt model for user retention",
        "design the data pipeline for this analytics use case",
        "sketch a Kafka topic layout for these events",
        "help me structure the transformation logic in dbt",
        "design the incremental refresh strategy for this table",
        "propose a schema for this event stream",
        "help me set up the data ingestion for this API",
        "plan the batch pipeline for the nightly rollup",
    ),
    should_not_fire=(
        "write a SQL query to get last-month signups",
        "review my Airflow DAG",
        "run the dbt build",
        "explain what a data warehouse is",
        "design an application backend",
        "write me a REST API",
    ),
)


API_DESIGNER = Template(
    name="api-designer",
    description=(
        "Designs REST endpoints, GraphQL schemas, and service contracts. Use "
        "when the user says 'design an API' or 'sketch the endpoints for this'."
    ),
    summary="Designs REST endpoints, GraphQL schemas, and service contracts.",
    should_fire=(
        "design a REST API for this feature",
        "sketch the endpoints for this service",
        "propose a GraphQL schema for these entities",
        "help me design the API for the checkout flow",
        "map out the endpoints for this resource",
        "design the request/response shapes for these operations",
        "propose the API contract between these services",
        "outline the endpoints and payloads for this microservice",
        "help me structure the public API for this SDK",
        "design the URL paths and verbs for this resource",
    ),
    should_not_fire=(
        "implement this endpoint",
        "review my API for issues",
        "generate API docs from my code",
        "write tests for the API",
        "design the database schema",
        "explain what REST is",
    ),
)


SKILL_CREATOR = Template(
    name="skill-creator",
    description=(
        "Helps author and improve Claude skills. Use when the user says "
        "'write a SKILL.md', 'tune this skill description', or 'draft an "
        "eval.yaml'."
    ),
    summary="Helps author and improve Claude skills.",
    should_fire=(
        "help me write a Claude skill for this task",
        "create a SKILL.md for the code-reviewer",
        "scaffold a new skill for handling PRs",
        "author a Claude skill that generates SQL",
        "improve the trigger accuracy of my SKILL.md",
        "help me tune the description on this skill",
        "generate a starter eval.yaml for my skill",
        "write a new agent skill for this workflow",
        "help me structure a SKILL.md for the security audit tool",
        "author a skill spec that will fire on the right prompts",
    ),
    should_not_fire=(
        "run my Claude skill",
        "explain what a Claude skill is",
        "review my SKILL.md for issues",
        "install a Claude skill from the marketplace",
        "list my installed skills",
        "write me a Python function",
    ),
)


TEMPLATES: dict[str, Template] = {
    t.name: t
    for t in (
        CODE_REVIEWER,
        REFACTORER,
        SQL_GENERATOR,
        DOCS_WRITER,
        TEST_WRITER,
        SECURITY_AUDITOR,
        DEBUGGER,
        DATA_ENGINEER,
        API_DESIGNER,
        SKILL_CREATOR,
    )
}


def list_templates() -> list[Template]:
    """Return templates in the same order they appear above (stable, curated)."""
    return list(TEMPLATES.values())


def get_template(name: str) -> Template | None:
    return TEMPLATES.get(name)
