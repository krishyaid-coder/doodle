# security-auditor eval suite

## Scope

Skills that check existing code for security vulnerabilities: injection, XSS, CSRF, auth weaknesses, hardcoded secrets, CVE-affected dependencies, OWASP-class issues. Read-side security work only.

## Why the should_not_fire prompts are tricky

- **General code review ≠ security review.** Both scan code, but style/correctness bugs are not the security-auditor's job.
- **Teaching ≠ auditing.** "Explain what SQL injection is" is education.
- **Writing security features ≠ auditing.** "Write a new auth system" is authoring.
- **Policy writing ≠ code auditing.** Document generation is a different skill.

## Adapting for your specific tool

- **Language-scoped** — narrow to a specific language ("audit my Python", "audit my Node.js").
- **Compliance-scoped** — SOC 2, PCI, HIPAA-focused audits are meaningfully different. Add compliance keywords to `should_fire` if your skill targets those.
- **Layer-scoped** — application-code security vs infrastructure-as-code security are different problem domains.
