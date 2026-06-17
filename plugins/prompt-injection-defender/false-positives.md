# False Positive Log

## 2026-06-02

**File:** `src/test/java/bet/fanatics/scorecards/testutils/AbstractIntegrationTest.java`  
**Triggered rule:** `[Context Manipulation] Instruction in single-line comment` (MEDIUM severity)  
**Content that triggered it:** Standard Java `//` inline comments in a Spring Boot integration test class — specifically documentation comments inside `@BeforeEach`/`@AfterEach` methods explaining test infrastructure behavior (e.g., `// Give async tasks time to complete before Spring shuts down EntityManagerFactory`).  
**Why it's a false positive:** The file is checked-in Java source code in a known project repo. The comments are legitimate technical documentation, not instructions to the model. No persona changes, no safety bypasses, no encoded content.  
**Suggested fix:** Tighten the `Instruction in single-line comment` pattern to require imperative verbs directed at an AI agent (e.g., "ignore", "disregard", "you are now") rather than firing on any comment that resembles a sentence.

---

## 2026-06-17 — Claude Code task output files

**File:** `/private/tmp/claude-<pid>/tasks/<agent-id>.output`  
**Triggered rule:** `[Context Manipulation] System role in JSON structure` (MEDIUM severity)  
**Content that triggered it:** Claude Code serializes background agent conversations as newline-delimited JSON. Each line is a message object with a `"role"` field (e.g., `"role": "user"`, `"role": "assistant"`). The pattern `"(system|role|instruction|prompt)"\s*:\s*"` matches `"role": "user"` and `"role": "assistant"` throughout.  
**Why it's a false positive:** These files are Claude Code's own internal inter-agent communication logs written to `/tmp` by the CLI itself. They are not external content. The `"role"` key is a standard chat-message JSON field, not a prompt injection marker.  
**Suggested fix (two options):**
1. **Path exclusion:** Skip scanning files matching `/tmp/claude-*/tasks/*.output` — they are always Claude Code's own serialized task logs.
2. **Pattern tightening (preferred):** The `"System role in JSON structure"` pattern currently matches any `"role":` key. It should be restricted to only match `"role": "system"` (i.e., change the pattern from `"(system|role|...)"\s*:\s*"` to only fire when the *value* is `"system"`, not the key). The existing pattern `{"role"\s*:\s*"system"` (HIGH severity) already covers the true-positive case.

---

## 2026-06-17 — Plugin's own patterns.yaml (self-referential)

**File:** `/Users/tylerstapler/dotfiles/plugins/prompt-injection-defender/hooks/patterns.yaml`  
**Triggered rules:** Nearly every rule — HIGH and MEDIUM severity across all categories.  
**Content that triggered it:** `patterns.yaml` contains the attack patterns themselves as regex strings. The file necessarily contains strings like `ignore previous instructions`, `DAN mode`, `jailbreak`, leetspeak examples, Cyrillic/Greek homoglyph samples, etc. — all of which trigger the very rules they define.  
**Why it's a false positive:** The plugin is scanning its own rule definitions file.  
**Suggested fix:** Add the plugin's own directory to a hard-coded path exclusion list, or add a general exclusion for files whose path contains `prompt-injection-defender/`.
