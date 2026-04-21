---
description: "One-shot workflow for simple tasks and bug fixes that fit in a single context window. Skips artifacts and fresh-session requirements."
argument-hint: "[task description]"
user-invocable: true
---

# sdd:quick

Lightweight end-to-end workflow for tasks simple enough to complete in one context window. No artifacts written, no phase gates, no fresh session required.

## When to use this

- Bug fixes (1–3 files)
- Small, well-scoped tasks ("add this field", "fix this edge case")
- Refactors within a single module
- Anything you can describe in one sentence

**When NOT to use this**: new services, multi-epic features, anything touching more than ~5 files, or anything requiring architecture decisions. Use `/sdd:1-ideate` instead.

## Instructions

1. **Clarify the task.**

   If `$1` was provided, use it as the task description and skip this step. Otherwise use `AskUserQuestion`:
   ```
   header: "Task type"
   question: "What needs to be done?"
   options:
     - "Fix a bug (I'll describe it via Other)"
     - "Add a small feature or field"
     - "Refactor or clean up existing code"
     - "Other — I'll describe it"
   ```

   Ask ONE follow-up via `AskUserQuestion` if genuinely needed (e.g. which file, which behaviour is expected). Do not interview — this is a quick path.

2. **Read before touching.**

   Read the relevant files. Form a clear mental model of what exists before proposing any change. For bugs:
   - Read the error/stack trace fully
   - Check `git log --oneline -10` for recent related changes
   - State the root cause hypothesis explicitly: "The root cause is X because Y"

3. **Plan inline (no file written).**

   State in 2–5 bullet points exactly what you will change and why. Confirm with the user if the scope is larger than expected.

4. **Implement.**

   Make the changes. For bugs, write a regression test that would have caught this. For features, write tests covering the happy path and one error path.

5. **Verify.**

   **Iron Law: No completion claim without running tests and showing output.**

   Run the relevant tests using the appropriate command for the stack. Show the output. Only claim success after seeing green.

6. **Output a brief summary:**

   ```
   ✅ Done

   What changed: <1–2 sentences>
   Files touched: <list>
   Tests: <N> passing
   Root cause (if bug): <one sentence>
   ```

   Then use `AskUserQuestion`:
   ```
   header: "Next step"
   question: "Ready to commit and push?"
   options:
     - "Yes — commit and push now"
     - "Let me review the diff first"
     - "Commit locally but don't push yet"
   ```
