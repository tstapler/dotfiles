---
name: test-driven-development
description: Enforce Red-Green-Refactor TDD cycle. Use when implementing any new class or method — write the failing test first, then make it pass. Never write production code before a failing test exists.
---

# Test-Driven Development

## Iron Law

**No production code without a failing test first.**

If you have written production code before a failing test:
1. Delete the production code
2. Write the failing test
3. Make it pass with minimal code
4. Then refactor

There are no exceptions. "This is too simple to need a test first" is rationalisation.

## Red-Green-Refactor Cycle

### RED — Write the failing test

1. Write the test for the behaviour you want
2. **Verify the test fails** before writing any production code.
   If you didn't watch it fail, you don't know if it tests the right thing.

### GREEN — Write minimal production code

Write the smallest amount of production code that makes the test pass.
Do not add logic that isn't required by a failing test.

### REFACTOR — Clean up

Clean the code while keeping tests green:
- Extract methods, rename for clarity, remove duplication
- Tests must still pass after every refactor step

## Required Test Cases Per Method

For each public method, write at minimum:
- Happy path (normal success)
- Error path (dependency throws or returns empty/null)
- Edge case (null, empty collection, boundary value)

## Anti-Patterns to Refuse

| Thought | Reality |
|---------|---------|
| "This is too simple to need a test" | Simple code breaks too. Write the test. |
| "I'll write tests after to save time" | You won't. The test discovers design flaws. |
| "The test would just mirror the implementation" | Then the implementation is too tightly coupled. |
| "Integration tests cover this" | Unit tests run in milliseconds. Write both. |
