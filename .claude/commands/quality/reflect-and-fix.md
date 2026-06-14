---
description: Post-mortem cycle that turns fixed bugs into structural enforcement. For each bug just fixed, classifies the root cause, finds the earliest possible detection point on the enforcement ladder (compile → lint → test → checklist), implements it, and verifies it would have caught the original bug. Goal is to eliminate the class, not just the instance.
prompt: |
  # Reflect & Fix — Shift Left After Every Bug

  After fixing bugs, the work isn't done until recurrence is structurally impossible.
  Run a 4-phase post-mortem that produces **runnable enforcement** (tests, lint rules,
  type changes) — not documentation or promises.

  ## Phase 1 — Enumerate

  From the current session context, list every bug that was fixed. For each state:
  - One sentence: what went wrong
  - One sentence: what correct behavior looks like

  If bugs aren't obvious from context, ask the user to list them before continuing.

  ## Phase 2 — Classify

  Apply this taxonomy to each bug. Pick the **primary** failure mode.

  | Category | Signature | Why it slips through |
  |----------|-----------|---------------------|
  | **Semantic/Intent** | Syntactically correct, semantically wrong — wrong default, wrong condition, wrong constant | Static analysis cannot detect intent; only a test asserting the intent can |
  | **Framework Pattern Misuse** | Valid code in wrong Compose/coroutine/lifecycle context — `remember` without key, scope escape, wrong dispatcher | Rule exists but not enabled, or rule has a detection gap |
  | **API Contract Gap** | Caller omits a required step the interface doesn't enforce — permission request, initialisation, annotation | Interface doesn't express the contract at the type level |
  | **Type Safety Gap** | Nullable mishandled, wrong type, missing discriminant | Type isn't leveraged; a value class or sealed type would prevent it |
  | **Integration Gap** | Two individually-correct components interact incorrectly across a seam | Unit tests with mocks pass; the seam is never exercised together |

  Fill this table before proceeding to Phase 3:

  | Bug | Category | Why it slipped through | Earliest detection |
  |-----|----------|----------------------|-------------------|
  | ... | ... | ... | ... |

  ## Phase 3 — Implement Enforcement

  Work down the **enforcement ladder** — implement at the highest (earliest) level achievable.
  Never accept level 5 when 1–4 is reachable. "We'll be more careful" is not a system.

  ```
  1. Compile time  → sealed class, @RequiresOptIn, non-nullable type, value class
  1b. Type-Driven Design gate (see below — must be evaluated before reaching for lint)
  2. Lint          → enable existing detekt/Android Lint rule, or write custom buildSrc rule
  3. Unit test     → asserts the exact failed behavior; must FAIL against pre-fix code
  4. Integration   → exercises both sides of a seam with minimal mocking
  5. Checklist     → CLAUDE.md entry only when 1–4 are genuinely not achievable
  ```

  ### Level 1b — Type-Driven Design Gate (mandatory before writing a lint rule)

  Before writing a lint rule, apply the `type-driven-design` skill to evaluate whether the
  type system can eliminate this class of error entirely. A lint rule catches the pattern
  after it's written; a type change makes the wrong pattern impossible to write.

  Ask these questions in order. Stop at the first "yes" and implement it instead of a lint rule.

  **1. Can the wrong usage be made unrepresentable?**
  - Is there a *different type* for the return of the API that would prevent the bad pattern?
  - Can a smart constructor, phantom type, or value class make the invalid state impossible to construct?
  - Example: if `key = { it.uuid }` is wrong and `key = { it.uuid.value }` is right, can we expose a
    `fun PageUuid.asLazyKey(): String = value` that makes the intent explicit — and optionally mark
    the direct `uuid` accessor `@RequiresOptIn(level = ERROR)` in key-lambda contexts?

  **2. Can the API be reshaped to only accept valid inputs?**
  - Can the function signature accept a stronger type instead of `Any`?
  - Can you wrap the call site in a typed helper that encodes the correct behavior?
  - Example: `fun <T> LazyListScope.typedItems(items: List<T>, key: (T) -> String, ...)` — forces
    the key to be a `String`, not `Any`, catching value class mistakes at compile time.

  **3. Can typestate or sealed types prevent the transition?**
  - Does the bug represent an invalid state transition (calling X before Y, using result in wrong phase)?
  - If so, a typestate or sealed interface may be the right tool.

  **4. Can the correct path be made ergonomically dominant?**
  - Even if you can't block the wrong path, can you make the right path the shortest one?
  - If yes, implement it as a complement to the lint rule, not instead of it.

  **Verdict table** — fill this in before proceeding to lint:

  | TDD question | Answer | Evidence |
  |---|---|---|
  | Wrong usage unrepresentable via types? | yes / no / partial | reason |
  | API reshape possible? | yes / no / partial | reason |
  | Typestate/sealed applicable? | yes / no | reason |
  | Ergonomic dominant path available? | yes / no | what it looks like |

  **If any answer is "yes"**: implement the type change. It replaces the lint rule — do not add both
  unless the type change only partially covers the class.

  **If all answers are "no" or "partial"**: proceed to lint (Level 2), but document *why* the type
  system cannot close this gap in the lint rule's KDoc. This is the evidence that Level 1 was
  genuinely evaluated, not skipped.

  **This session's example** — `PageUuid` as `LazyColumn` key:
  - *Wrong usage unrepresentable?* Partial — can add `fun PageUuid.asLazyKey(): String = value` for
    ergonomics, but cannot block direct `.uuid` access since `key` accepts `Any`.
  - *API reshape possible?* No — `items(key = (T) -> Any)` is Compose's API; we can't change it.
  - *Typestate/sealed?* No — not a state machine problem.
  - *Ergonomic path?* Yes — `asLazyKey()` extension. Implement as complement.
  - **Verdict**: type change partially helps but cannot close the gap → lint rule is the primary
    enforcement. Document in rule KDoc: "Compose's `key` parameter accepts `Any`; type-level
    prevention requires changing the Compose API."

  ### Semantic/Intent → Write the failing test

  Write a test that:
  - Sets up the exact conditions that produced the bug
  - Asserts the correct outcome
  - **Must fail against the pre-fix code** — revert and run it to confirm, or reason through why it fails

  ```kotlin
  @Test
  fun `[the wrong thing] is [the right thing]`() {
      // Arrange: reproduce the exact failure conditions
      // Act
      // Assert — this assertion must fail against pre-fix code
  }
  ```

  Place in the appropriate test source set (`businessTest` for logic, `jvmTest` for JVM integration).

  ### Framework Pattern Misuse → Lint rule

  1. Check `detekt.yml` and active rule sets (e.g. `io.nlopez.compose.rules`) for an existing rule
  2. If it exists: enable it (`active: true`), address any existing violations, run `./gradlew detekt`
  3. If it doesn't exist: write a custom rule in `buildSrc/src/main/kotlin/dev/stapler/detekt/`

  Custom rule skeleton for this project:
  ```kotlin
  class YourRuleName(config: Config = Config.empty) : Rule(config) {
      override val issue = Issue("YourRuleName", Severity.Defect, "description", Debt.FIVE_MINS)
      override fun visitXxx(node: KtXxx) {
          super.visitXxx(node)
          // detect bad pattern → report(CodeSmell(issue, Entity.from(node), "message"))
      }
  }
  ```
  - Register it in `SteleKitRuleSetProvider`
  - Add it to `detekt.yml` with `active: true`
  - Write a test that fires on the bad pattern and is silent on the good pattern
  - Verify: temporarily revert the fix and confirm `./gradlew detekt` reports the violation

  ### API Contract Gap → Encode the contract in the type

  Prefer in this order:
  1. **Required constructor parameter** — if it's omitted, it won't compile
  2. **`@RequiresOptIn(level = ERROR)`** — callers must explicitly opt in; compiler enforces it
  3. **Lint rule** — flag call sites that use the API without the prerequisite step

  Before (contract documented but not enforced):
  ```kotlin
  class Foo(val context: Context)  // caller must also request RECORD_AUDIO — easy to forget
  ```
  After (contract enforced at the type level):
  ```kotlin
  class Foo(val context: Context, val requestPermission: (suspend () -> Boolean)? = null)
  ```

  ### Type Safety Gap → Harden the type

  - Replace `Type?` with `Type` where null is not a valid state
  - Replace stringly-typed values with sealed classes or enums
  - Use `@JvmInline value class` to prevent primitive confusion
  - Use sealed states to make all cases explicit and exhaustive

  ### Integration Gap → Integration test

  Write a test that:
  - Instantiates **both** components — no mocking the seam itself
  - Uses in-memory fakes for external dependencies (not mocks of the components under test)
  - Exercises the interaction path that was broken
  - Must fail against pre-fix code

  ## Phase 4 — Verify

  For **every** enforcement added, answer: would this have caught the original bug?

  | Enforcement added | Pre-fix behaviour | Verdict |
  |-------------------|------------------|---------|
  | New test `...` | fails ✓ / passes ✗ | catches it / insufficient |
  | Detekt rule `...` | fires ✓ / silent ✗ | catches it / insufficient |
  | Type change `...` | doesn't compile ✓ / compiles ✗ | catches it / insufficient |

  If any row says "insufficient", escalate to a stronger level. Do not close out until
  every bug has at least one enforcement that would have caught it.

  ## Anti-patterns to reject

  - Adding a CLAUDE.md note instead of a test — notes rot, tests don't
  - Writing a test that mocks the broken component — it won't catch the regression
  - Writing a detekt rule with no test for the rule itself — rules break silently on refactors
  - Stopping at "the fix is in" — the class is still alive until enforcement is in place
---

# Reflect & Fix — Shift Left After Every Bug

After fixing bugs, the work isn't done until recurrence is **structurally impossible**.
This command runs a 4-phase post-mortem that produces runnable enforcement (tests, lint
rules, type changes) — not documentation or promises to be careful.

## The Enforcement Ladder

Always implement at the **earliest** achievable level. Never accept level 5 when 1–4 is reachable.

```
1.  Compile time          → sealed class, @RequiresOptIn, non-nullable type, value class
1b. Type-Driven Design    → evaluate before lint — can the type system eliminate this class?
2.  Lint                  → existing detekt/Android Lint rule, or custom buildSrc rule
3.  Unit test             → asserts exact failed behavior; must fail against pre-fix code
4.  Integration           → exercises both sides of a seam with minimal mocking
5.  Checklist             → CLAUDE.md entry only when 1–4 genuinely not achievable
```

**Level 1b is mandatory.** Before writing any lint rule, use the `type-driven-design` skill to
evaluate whether the type system can close the gap entirely. A lint rule catches bad patterns
after they're written; a type change makes them impossible to write. Document the verdict — if
types cannot close the gap, say why in the lint rule's KDoc.

## Root Cause Taxonomy

| Category | Signature | Earliest enforcement |
|----------|-----------|---------------------|
| **Semantic/Intent** | Wrong default, wrong condition, wrong constant — code is syntactically valid | Unit/integration test |
| **Framework Pattern Misuse** | Valid code in wrong Compose/coroutine context — `remember` without key, scope escape | Lint rule (enable existing or write custom) |
| **API Contract Gap** | Caller omits required setup step — permission request, annotation, initialisation | Type-level enforcement or `@RequiresOptIn` |
| **Type Safety Gap** | Nullable mishandled, wrong type, primitive confusion | Kotlin type system (sealed class, value class) — then TDD gate |
| **Integration Gap** | Individually-correct components interact incorrectly at a seam | Integration test spanning the seam |

## Phases

**Phase 1 — Enumerate**: list every bug fixed; one sentence each on what went wrong and what correct looks like.

**Phase 2 — Classify**: assign each bug a category and identify why the current tooling didn't catch it.

**Phase 3 — Implement**: for each bug, run the Level 1b TDD gate first, then implement enforcement at the highest achievable level on the ladder.

**Phase 4 — Verify**: confirm each enforcement would have caught the original bug (revert and test, or reason through it). If not, escalate.

## Anti-patterns

- Noting the fix in CLAUDE.md instead of writing a test — notes rot, tests don't
- Mocking the broken component in the test — it won't catch the regression
- Writing a detekt rule with no test for the rule itself — rules break silently
- Stopping at "the fix is in" before enforcement is in place
- **Skipping the TDD gate and going straight to lint** — always evaluate Level 1b first
