# False Positive Log

## 2026-06-02

**File:** `src/test/java/bet/fanatics/scorecards/testutils/AbstractIntegrationTest.java`  
**Triggered rule:** `[Context Manipulation] Instruction in single-line comment` (MEDIUM severity)  
**Content that triggered it:** Standard Java `//` inline comments in a Spring Boot integration test class — specifically documentation comments inside `@BeforeEach`/`@AfterEach` methods explaining test infrastructure behavior (e.g., `// Give async tasks time to complete before Spring shuts down EntityManagerFactory`).  
**Why it's a false positive:** The file is checked-in Java source code in a known project repo. The comments are legitimate technical documentation, not instructions to the model. No persona changes, no safety bypasses, no encoded content.  
**Suggested fix:** Tighten the `Instruction in single-line comment` pattern to require imperative verbs directed at an AI agent (e.g., "ignore", "disregard", "you are now") rather than firing on any comment that resembles a sentence.
