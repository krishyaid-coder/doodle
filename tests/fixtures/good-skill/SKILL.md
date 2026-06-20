---
name: good-skill
description: Reviews staged Python diffs for security issues. Use when the user says 'review my changes' or runs git diff before committing.
license: MIT
---

# Good Skill

A clean reference skill with a tight description, concrete trigger phrasing,
and a short body that stays under the soft cap.

## What it does

Walks the staged diff line by line and flags common security smells:
hardcoded secrets, SQL injection patterns, and unsafe deserialization.

## How to invoke

Trigger this skill when the user is preparing to commit or asks for a
security pass on staged changes.
