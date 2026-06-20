---
name: abs-path
description: Demonstrates absolute-path leakage. Use when testing the body/absolute-user-path rule.
---

# Absolute Path

Read the config from /Users/alice/.config/skill.json and write results to ~/Downloads/out.

```bash
# This path inside a fence should be ignored:
cat /Users/example/example.txt
```

The line above (outside the fence) should still flag.
