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

---

## 2026-06-18 — TypeScript JSDoc "highest priority" in domain type

**File:** `web-app/src/lib/hooks/useBacklogService.ts`  
**Triggered rule:** `[Instruction Override] Priority manipulation attempt` (MEDIUM severity)  
**Content that triggered it:** JSDoc comment on the `priority` field of the `BacklogItem` interface: `/** 1 = highest priority, 5 = lowest */`. The phrase "highest priority" matches the pattern `(highest|top|maximum|critical)\s+priority`.  
**Why it's a false positive:** This is a standard documentation comment in a TypeScript source file explaining the numeric range of a domain model field. "Highest priority" refers to software ticket priority levels (P1 = highest), not AI instruction precedence.  
**Suggested fix:** The `Priority manipulation attempt` pattern should require additional AI-targeting context after "priority" — e.g., require the word "instruction", "override", "over", or "than" to follow it. Bare `highest priority` in a source file doc comment is a common domain concept (Jira-style P1–P5, OS thread priorities, etc.) and should not fire without a clear AI-targeting signal.

---

## 2026-06-23 — reflect-and-fix.md skill file

**File:** `/Users/tylerstapler/.claude/commands/quality/reflect-and-fix.md`
**Triggered rule:** `[Role-Playing/DAN] No-rules mode request` (HIGH severity)
**Content that triggered it:** The skill file's enforcement-ladder taxonomy and anti-pattern descriptions. Likely matched on phrases describing what bad patterns to avoid (e.g. terms related to "no rules", "bypass", or similar in the context of describing enforcement gaps the skill is designed to prevent).
**Why it's a false positive:** This is a checked-in personal skill definition in `~/.claude/commands/`. It is a structured process document for post-mortem analysis, not a prompt injection attempt. It does not attempt to override persona, bypass safety measures, or enable alternative modes.
**Decision:** This is the fifth false positive with zero confirmed true positives. Plugin disabled as of this date.

---

## 2026-06-18 — MDD plan.md with state-machine terminology

**File:** `/Users/tylerstapler/dotfiles/project_plans/ssh-bastion/implementation/plan.md`  
**Triggered rule:** `[Instruction Override] Attempts to reset context` (HIGH severity)  
**Content that triggered it:** Story D.9 in the plan describes knock-sshd's per-IP state machine. The phrase "reset state for that IP" (describing the daemon resetting its knock sequence tracker when a TTL expires) matched the instruction-override pattern looking for "reset" combined with context/state terminology.  
**Why it's a false positive:** This is a checked-in planning document in the dotfiles repo describing software behavior — not a prompt injection attempt. "Reset state" here refers to in-memory application state (a `DashMap` entry), not session/conversation context.  
**Suggested fix:** The `Instruction Override` pattern matching "reset" should require additional AI-targeting context (e.g., "reset your instructions", "reset context", "reset conversation") rather than firing on bare "reset state" which is common in software design documents.
