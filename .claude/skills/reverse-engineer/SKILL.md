---
name: reverse-engineer
description: Methodically decompose existing code and projects to extract architectural
  patterns, functional logic, and business rules. Use this skill when preparing a
  comprehensive implementation plan for re-engineering, migration, or documentation
  of legacy systems.
---

# Reverse Engineer Skill

This skill outlines a systematic process for dissecting an existing codebase or project. The goal is to move from "raw code" to a "comprehensive functional blueprint" that can be used by another agent to implement a new version, migrate the system, or provide high-fidelity documentation.

## Core Instructions

### When to Use This Skill
- **Migration**: Moving from one language/framework to another (e.g., Cargo to Bazel, TS to Rust).
- **Re-implementation**: Building a "clean" version of a legacy feature.
- **Auditing**: Understanding complex, undocumented logic.
- **Agent Hand-off**: Preparing a detailed plan for a "Developer Agent" to execute.

### The Reverse Engineering Workflow

#### Phase 1: Structural Discovery (Mapping)
1. **Identify Entry Points**: Find main functions, API routes, event listeners, or CLI command definitions.
2. **Map Dependencies**: List internal modules and external libraries. Identify the "core" of the project vs. the "shell" (infrastructure).
3. **Walk the Tree**: Systematically list the file structure and the responsibility of each directory.

#### Phase 2: Behavioral Extraction (Logic)
1. **Isolate State**: Identify where data lives (DB schemas, in-memory stores, config files) and how it changes.
2. **Trace Data Flow**: Follow a single "request" or "action" from the entry point through the logic to the side effect (e.g., writing to a file or returning an API response).
3. **Extract Business Rules**: Look for "pure" logic—validation rules, transformation algorithms, and decision trees—independent of the framework.

#### Phase 3: Architectural Synthesis (The Plan)
1. **Define the "What"**: Summarize the system's behavior in plain language, ignoring the current implementation's "how".
2. **Design the Target State**: Propose how this logic *should* look in the new system (using modern patterns like Hexagonal Architecture, Traits, etc.).
3. **Create the Implementation Plan**:
   - Break the work into **Atomic Tasks** (1-4 hours each).
   - Define clear **Acceptance Criteria** for each task.
   - Specify the **Validation Strategy** (which tests to write).

### Key Principles
- **Function over Form**: Focus on what the code *does*, not how it's currently written.
- **Isolate Side Effects**: Clearly separate logic from I/O (Database, Network, Filesystem).
- **Document the "Why"**: Look for comments or commit history that explain non-obvious logic.

### Common Pitfalls
- ❌ **Copying Spagetti**: Don't just translate code line-by-line. Extract the logic and re-implement it idiomatically.
- ❌ **Missing Hidden Config**: Check environment variables and hidden dotfiles.
- ❌ **Ignoring Edge Cases**: Look for error handling blocks (catch, match Err, unwrap); these often contain the most important business rules.

## Progressive Context Loading
- For a checklist of language-specific patterns, see: [reference.md](references/reference.md)
- For an example of a completed reverse-engineering report, see: [examples.md](references/examples.md)

## Token Budget
- **Metadata**: ~100 tokens
- **SKILL.md**: ~1,200 tokens
- **Reference/Examples**: Loaded on-demand (~2,000 tokens)