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
  2. Lint          → enable existing detekt/Android Lint rule, or write custom buildSrc rule
  3. Unit test     → asserts the exact failed behavior; must FAIL against pre-fix code
  4. Integration   → exercises both sides of a seam with minimal mocking
  5. Checklist     → CLAUDE.md entry only when 1–4 are genuinely not achievable
  ```

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
1. Compile time  → sealed class, @RequiresOptIn, non-nullable type, value class
2. Lint          → existing detekt/Android Lint rule, or custom buildSrc rule
3. Unit test     → asserts exact failed behavior; must fail against pre-fix code
4. Integration   → exercises both sides of a seam with minimal mocking
5. Checklist     → CLAUDE.md entry only when 1–4 genuinely not achievable
```

## Root Cause Taxonomy

| Category | Signature | Earliest enforcement |
|----------|-----------|---------------------|
| **Semantic/Intent** | Wrong default, wrong condition, wrong constant — code is syntactically valid | Unit/integration test |
| **Framework Pattern Misuse** | Valid code in wrong Compose/coroutine context — `remember` without key, scope escape | Lint rule (enable existing or write custom) |
| **API Contract Gap** | Caller omits required setup step — permission request, annotation, initialisation | Type-level enforcement or `@RequiresOptIn` |
| **Type Safety Gap** | Nullable mishandled, wrong type, primitive confusion | Kotlin type system (sealed class, value class) |
| **Integration Gap** | Individually-correct components interact incorrectly at a seam | Integration test spanning the seam |

## Phases

**Phase 1 — Enumerate**: list every bug fixed; one sentence each on what went wrong and what correct looks like.

**Phase 2 — Classify**: assign each bug a category and identify why the current tooling didn't catch it.

**Phase 3 — Implement**: for each bug, implement enforcement at the highest achievable level on the ladder.

**Phase 4 — Verify**: confirm each enforcement would have caught the original bug (revert and test, or reason through it). If not, escalate.

## Anti-patterns

- Noting the fix in CLAUDE.md instead of writing a test — notes rot, tests don't
- Mocking the broken component in the test — it won't catch the regression
- Writing a detekt rule with no test for the rule itself — rules break silently
- Stopping at "the fix is in" before enforcement is in place
