---
name: ui-web-design-guidelines
description: "Audit UI code against 100+ web best practices - accessibility, focus states, forms, animation, typography, images, performance, dark mode, i18n. Use when asked to review UI or check accessibility."
---

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

> For generating a complete design system before auditing, apply the `ui-design-system` skill.

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use WebFetch to retrieve the latest rules. The fetched content contains all the rules and output format instructions.

## Usage

When a user provides a file or pattern argument:
1. Fetch guidelines from the source URL above
2. Read the specified files
3. Apply all rules from the fetched guidelines
4. Output findings using the format specified in the guidelines

If no files specified, ask the user which files to review.

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `ui-design-system` | Generate a design system before auditing new UI for compliance |
| `ui-react-best-practices` | Fix React-specific issues found during the audit |
| `ui-composition-patterns` | Refactor component architecture problems surfaced by the audit |
| `ui-playwright` | Automate regression tests for issues fixed after the audit |
