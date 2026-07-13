# api-designer eval suite

## Scope

Skills that design HTTP APIs, GraphQL schemas, and service contracts: endpoint layout, request/response shapes, resource modeling, verb selection. Design, not implementation, not documentation, not review.

## Why the should_not_fire prompts are tricky

- **Implementation ≠ design.** "Implement this endpoint" hands off to a code-writer.
- **Docs ≠ design.** Even OpenAPI generation happens after design.
- **Testing ≠ design.** Contract tests come after the contract exists.
- **Schema design ≠ API design.** Database schema is a different problem, though related.

## Adapting for your specific tool

- **Style-scoped** — REST vs GraphQL vs gRPC vs tRPC. Narrow the positive prompts to the style your skill knows.
- **Convention-scoped** — if your skill enforces a specific style guide (Google, Stripe, JSON:API), name it in the description.
- **Layer-scoped** — internal service-to-service APIs and public-facing APIs have very different design constraints.
