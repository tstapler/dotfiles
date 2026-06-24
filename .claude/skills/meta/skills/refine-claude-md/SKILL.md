---
description: Refactor CLAUDE.md to be concise with references to external documentation,
  minimizing token usage while maintaining prescriptive standards
prompt: "# Refine CLAUDE.md Files\n\nUse the prompt-engineering agent to analyze and\
  \ refactor CLAUDE.md files, extracting verbose content to external reference documents\
  \ while maintaining clear, actionable guidance.\n\n## Task\n\nRefine the CLAUDE.md\
  \ file at: ${1:-.claude/CLAUDE.md}\n\n## Context\n\nCLAUDE.md files can become bloated\
  \ with detailed standards, workflows, and guidelines. This command helps maintain\
  \ a clean, token-efficient structure by:\n\n1. **Keeping CLAUDE.md concise** - Only\
  \ high-level guidance and reference links\n2. **Converting complex workflows to\
  \ skills** - Use `/skill:create` for repeatable agent tasks\n3. **Extracting reference\
  \ content** - Move detailed documentation to specialized docs\n4. **Creating reference\
  \ index** - Link to external files and skills for detailed information\n5. **Maintaining\
  \ prescriptive standards** - Ensure all guidance remains accessible\n\n## Requirements\n\
  \nUse the @task prompt-engineering agent with the following objectives:\n\n### Analysis\
  \ Phase\n- Read the target CLAUDE.md file\n- Identify sections that are too verbose\
  \ (>100 lines or highly detailed)\n- **Categorize content by type**:\n  - **Complex\
  \ workflows/procedures** → Candidates for Agent Skills (use `/skill:create`)\n \
  \ - **Reference documentation** → Extract to `docs/` directory\n  - **Simple guidelines**\
  \ → Keep concise in CLAUDE.md\n- Evaluate which content can be extracted without\
  \ losing clarity\n- Check if a `docs/` or `.claude/docs/` directory exists for reference\
  \ files\n- Check if a `skills/` or `.claude/skills/` directory exists for agent\
  \ skills\n\n### Skill Creation Phase\nFor complex workflows that agents need to\
  \ execute repeatedly:\n- **Identify skill candidates**: Multi-step procedures, domain-specific\
  \ tasks, complex workflows\n- **Run `/skill:create [skill-name] [purpose] [location]`**\
  \ to create proper Agent Skills\n- Examples of good skill candidates:\n  - Database\
  \ optimization workflows\n  - Testing and debugging procedures\n  - Code refactoring\
  \ patterns\n  - Documentation generation processes\n  - Deployment and CI/CD workflows\n\
  - Agent Skills provide progressive disclosure and are more efficient than long CLAUDE.md\
  \ sections\n\n### Extraction Phase\nFor reference documentation:\n- Create a new\
  \ reference file in the appropriate `docs/` directory\n- Name files descriptively\
  \ (e.g., `python_standards.md`, `docker_workflow.md`)\n- Preserve all content, examples,\
  \ and formatting\n- Maintain internal links and cross-references\n\n### Refactoring\
  \ Phase\nUpdate CLAUDE.md to:\n- Replace verbose workflow sections with references\
  \ to Agent Skills\n- Replace reference content with concise summaries (2-5 lines)\
  \ + links to docs\n- Add clear references to both skills and documentation\n- Create\
  \ a \"Reference Documents Index\" section if multiple files extracted\n- Create\
  \ a \"Skills Index\" section if skills were created\n- Maintain logical flow and\
  \ discoverability\n\n### Validation Phase\n- Ensure all extracted content is properly\
  \ linked\n- Verify skills are properly created with SKILL.md files\n- Verify no\
  \ information was lost\n- Test that references to skills and docs are clear and\
  \ actionable\n- Check that CLAUDE.md remains comprehensive at high level\n- Confirm\
  \ skills follow best practices (progressive disclosure, token optimization)\n\n\
  ## Directory Structure\n\nThe agent should create or use these directories:\n\n\
  ```\n# For project-level CLAUDE.md\n.claude/\n├── CLAUDE.md          (main file\
  \ - keep concise)\n├── skills/            (Agent Skills for complex workflows)\n\
  │   ├── db-optimization/\n│   │   ├── SKILL.md\n│   │   └── scripts/\n│   ├── test-debugging/\n\
  │   │   └── SKILL.md\n│   └── ...\n└── docs/              (detailed reference docs)\n\
  \    ├── python_standards.md\n    ├── docker_workflow.md\n    ├── testing_guide.md\n\
  \    └── ...\n\n# For user-level ~/.claude/CLAUDE.md\n~/.claude/\n├── CLAUDE.md\
  \          (main file - keep concise)\n├── skills/            (Agent Skills for\
  \ complex workflows)\n│   ├── code-refactoring/\n│   │   ├── SKILL.md\n│   │   └──\
  \ scripts/\n│   ├── infrastructure-testing/\n│   │   └── SKILL.md\n│   └── ...\n\
  └── docs/              (detailed reference docs)\n    ├── refactoring_workflow.md\n\
  \    ├── infrastructure_testing.md\n    └── ...\n```\n\n## Output Expectations\n\
  \nThe agent will:\n1. ✅ Analyze current CLAUDE.md and identify verbose sections\n\
  2. ✅ Identify complex workflows suitable for Agent Skills\n3. ✅ Run `/skill:create`\
  \ for workflow sections (or provide guidance to do so)\n4. ✅ Create new reference\
  \ files in `docs/` directory for reference content\n5. ✅ Update CLAUDE.md with concise\
  \ summaries and links to skills/docs\n6. ✅ Add a \"Skills Index\" section if skills\
  \ were created\n7. ✅ Add a \"Reference Documents Index\" section if docs were extracted\n\
  8. ✅ Provide summary of changes and token savings\n9. ✅ Verify all links work and\
  \ content is preserved\n\n## Example Result\n\n### Before (Verbose CLAUDE.md)\n\
  ```markdown\n## Python Development\n\nAlways use `uv` for dependency management.\
  \ Follow these guidelines:\n\n### Code Quality Standards\n- Use Black with line\
  \ length 120\n- Use ruff for linting\n... (50+ more lines)\n\n### Testing Standards\n\
  - Write unit tests for all functions\n- Use pytest fixtures\n... (30+ more lines)\n\
  \n## Database Optimization Workflow\n\nWhen optimizing PostgreSQL databases:\n\n\
  1. Analyze the schema and identify tables with high cardinality\n2. Check for missing\
  \ indexes using pg_stat_user_tables\n3. Analyze query plans with EXPLAIN ANALYZE\n\
  4. Review connection pooling configuration\n5. Check for n+1 query patterns\n...\
  \ (100+ more lines of detailed workflow)\n\n## Docker Build Process\n\nFollow this\
  \ process for all Docker builds:\n\n1. Run make validate to check Dockerfile syntax\n\
  2. Build with --target development for testing\n3. Run integration tests in container\n\
  ... (60+ more lines)\n```\n\n### After (Concise CLAUDE.md with Skills)\n```markdown\n\
  ## Python Development\n\n- Always use `uv` for installing and manipulating python\
  \ dependencies\n- For complete Python coding standards, see `~/.claude/docs/python_standards.md`\n\
  \n## Database Optimization\n\n- Use the `db-optimization` skill for systematic PostgreSQL\
  \ optimization workflows\n- The skill provides progressive disclosure for schema\
  \ analysis, indexing, and query optimization\n- See `.claude/skills/db-optimization/`\
  \ for details\n\n## Docker Development\n\n- For Docker build and test workflows,\
  \ see `~/.claude/docs/docker_workflow.md`\n- Always run `make validate` before pushing\n\
  \n---\n\n## Skills Index\n\nSkills available for complex, repeatable workflows:\n\
  - **db-optimization** - Systematic PostgreSQL database optimization workflows\n\
  - **test-debugging** - Comprehensive test failure diagnosis and resolution\n\n##\
  \ Reference Documents Index\n\nAll detailed reference documentation is stored in\
  \ `~/.claude/docs/`:\n- **python_standards.md** - Complete Python coding guidelines\
  \ and best practices\n- **docker_workflow.md** - Docker build, test, and validation\
  \ workflows\n```\n\n## Usage Examples\n\n### Refine current project's CLAUDE.md\n\
  ```\n/meta:refine-claude-md\n```\n\n### Refine global user CLAUDE.md\n```\n/meta:refine-claude-md\
  \ ~/.claude/CLAUDE.md\n```\n\n### Refine specific project CLAUDE.md\n```\n/meta:refine-claude-md\
  \ /path/to/project/.claude/CLAUDE.md\n```\n\n## Quality Standards\n\nThe refined\
  \ structure will:\n- Reduce CLAUDE.md token count by 50-80%\n- Convert complex workflows\
  \ to Agent Skills for progressive disclosure and token efficiency\n- Maintain all\
  \ prescriptive standards in accessible locations (skills and docs)\n- Create logical,\
  \ well-organized reference documents\n- Use clear, actionable language in summaries\n\
  - Preserve examples in reference docs and skill instructions\n- Enable easy navigation\
  \ through skills and reference links\n- Follow Agent Skills best practices (progressive\
  \ disclosure, token optimization)\n- Follow established documentation patterns (Diátaxis\
  \ when appropriate)\n\n## Success Criteria\n\nA successful refactoring includes:\n\
  1. CLAUDE.md is under 200 lines (ideally under 150)\n2. Complex workflows converted\
  \ to Agent Skills with proper SKILL.md files\n3. All detailed reference content\
  \ moved to docs\n4. Clear \"Skills Index\" section (if skills created)\n5. Clear\
  \ \"Reference Documents Index\" section (if docs extracted)\n6. No loss of information\
  \ or guidance\n7. Improved token efficiency (50-80% reduction)\n8. Maintained prescriptive\
  \ nature\n9. Easy discoverability of skills and detailed content\n10. Skills follow\
  \ best practices: progressive disclosure, token optimization, security\n"
---

# Refine CLAUDE.md Files

Use the prompt-engineering agent to analyze and refactor CLAUDE.md files, extracting verbose content to external reference documents while maintaining clear, actionable guidance.

## Task

Refine the CLAUDE.md file at: ${1:-.claude/CLAUDE.md}

## Context

CLAUDE.md files can become bloated with detailed standards, workflows, and guidelines. This command helps maintain a clean, token-efficient structure by:

1. **Keeping CLAUDE.md concise** - Only high-level guidance and reference links
2. **Converting complex workflows to skills** - Use `/skill:create` for repeatable agent tasks
3. **Extracting reference content** - Move detailed documentation to specialized docs
4. **Creating reference index** - Link to external files and skills for detailed information
5. **Maintaining prescriptive standards** - Ensure all guidance remains accessible

## Requirements

Use the @task prompt-engineering agent with the following objectives:

### Analysis Phase
- Read the target CLAUDE.md file
- Identify sections that are too verbose (>100 lines or highly detailed)
- **Categorize content by type**:
  - **Complex workflows/procedures** → Candidates for Agent Skills (use `/skill:create`)
  - **Reference documentation** → Extract to `docs/` directory
  - **Simple guidelines** → Keep concise in CLAUDE.md
- Evaluate which content can be extracted without losing clarity
- Check if a `docs/` or `.claude/docs/` directory exists for reference files
- Check if a `skills/` or `.claude/skills/` directory exists for agent skills

### Skill Creation Phase
For complex workflows that agents need to execute repeatedly:
- **Identify skill candidates**: Multi-step procedures, domain-specific tasks, complex workflows
- **Run `/skill:create [skill-name] [purpose] [location]`** to create proper Agent Skills
- Examples of good skill candidates:
  - Database optimization workflows
  - Testing and debugging procedures
  - Code refactoring patterns
  - Documentation generation processes
  - Deployment and CI/CD workflows
- Agent Skills provide progressive disclosure and are more efficient than long CLAUDE.md sections

### Extraction Phase
For reference documentation:
- Create a new reference file in the appropriate `docs/` directory
- Name files descriptively (e.g., `python_standards.md`, `docker_workflow.md`)
- Preserve all content, examples, and formatting
- Maintain internal links and cross-references

### Refactoring Phase
Update CLAUDE.md to:
- Replace verbose workflow sections with references to Agent Skills
- Replace reference content with concise summaries (2-5 lines) + links to docs
- Add clear references to both skills and documentation
- Create a "Reference Documents Index" section if multiple files extracted
- Create a "Skills Index" section if skills were created
- Maintain logical flow and discoverability

### Validation Phase
- Ensure all extracted content is properly linked
- Verify skills are properly created with SKILL.md files
- Verify no information was lost
- Test that references to skills and docs are clear and actionable
- Check that CLAUDE.md remains comprehensive at high level
- Confirm skills follow best practices (progressive disclosure, token optimization)

## Directory Structure

The agent should create or use these directories:

```
# For project-level CLAUDE.md
.claude/
├── CLAUDE.md          (main file - keep concise)
├── skills/            (Agent Skills for complex workflows)
│   ├── db-optimization/
│   │   ├── SKILL.md
│   │   └── scripts/
│   ├── test-debugging/
│   │   └── SKILL.md
│   └── ...
└── docs/              (detailed reference docs)
    ├── python_standards.md
    ├── docker_workflow.md
    ├── testing_guide.md
    └── ...

# For user-level ~/.claude/CLAUDE.md
~/.claude/
├── CLAUDE.md          (main file - keep concise)
├── skills/            (Agent Skills for complex workflows)
│   ├── code-refactoring/
│   │   ├── SKILL.md
│   │   └── scripts/
│   ├── infrastructure-testing/
│   │   └── SKILL.md
│   └── ...
└── docs/              (detailed reference docs)
    ├── refactoring_workflow.md
    ├── infrastructure_testing.md
    └── ...
```

## Output Expectations

The agent will:
1. ✅ Analyze current CLAUDE.md and identify verbose sections
2. ✅ Identify complex workflows suitable for Agent Skills
3. ✅ Run `/skill:create` for workflow sections (or provide guidance to do so)
4. ✅ Create new reference files in `docs/` directory for reference content
5. ✅ Update CLAUDE.md with concise summaries and links to skills/docs
6. ✅ Add a "Skills Index" section if skills were created
7. ✅ Add a "Reference Documents Index" section if docs were extracted
8. ✅ Provide summary of changes and token savings
9. ✅ Verify all links work and content is preserved

## Example Result

### Before (Verbose CLAUDE.md)
```markdown
## Python Development

Always use `uv` for dependency management. Follow these guidelines:

### Code Quality Standards
- Use Black with line length 120
- Use ruff for linting
... (50+ more lines)

### Testing Standards
- Write unit tests for all functions
- Use pytest fixtures
... (30+ more lines)

## Database Optimization Workflow

When optimizing PostgreSQL databases:

1. Analyze the schema and identify tables with high cardinality
2. Check for missing indexes using pg_stat_user_tables
3. Analyze query plans with EXPLAIN ANALYZE
4. Review connection pooling configuration
5. Check for n+1 query patterns
... (100+ more lines of detailed workflow)

## Docker Build Process

Follow this process for all Docker builds:

1. Run make validate to check Dockerfile syntax
2. Build with --target development for testing
3. Run integration tests in container
... (60+ more lines)
```

### After (Concise CLAUDE.md with Skills)
```markdown
## Python Development

- Always use `uv` for installing and manipulating python dependencies
- For complete Python coding standards, see `~/.claude/docs/python_standards.md`

## Database Optimization

- Use the `db-optimization` skill for systematic PostgreSQL optimization workflows
- The skill provides progressive disclosure for schema analysis, indexing, and query optimization
- See `.claude/skills/db-optimization/` for details

## Docker Development

- For Docker build and test workflows, see `~/.claude/docs/docker_workflow.md`
- Always run `make validate` before pushing

---

## Skills Index

Skills available for complex, repeatable workflows:
- **db-optimization** - Systematic PostgreSQL database optimization workflows
- **test-debugging** - Comprehensive test failure diagnosis and resolution

## Reference Documents Index

All detailed reference documentation is stored in `~/.claude/docs/`:
- **python_standards.md** - Complete Python coding guidelines and best practices
- **docker_workflow.md** - Docker build, test, and validation workflows
```

## Usage Examples

### Refine current project's CLAUDE.md
```
/meta:refine-claude-md
```

### Refine global user CLAUDE.md
```
/meta:refine-claude-md ~/.claude/CLAUDE.md
```

### Refine specific project CLAUDE.md
```
/meta:refine-claude-md /path/to/project/.claude/CLAUDE.md
```

## Quality Standards

The refined structure will:
- Reduce CLAUDE.md token count by 50-80%
- Convert complex workflows to Agent Skills for progressive disclosure and token efficiency
- Maintain all prescriptive standards in accessible locations (skills and docs)
- Create logical, well-organized reference documents
- Use clear, actionable language in summaries
- Preserve examples in reference docs and skill instructions
- Enable easy navigation through skills and reference links
- Follow Agent Skills best practices (progressive disclosure, token optimization)
- Follow established documentation patterns (Diátaxis when appropriate)

## Success Criteria

A successful refactoring includes:
1. CLAUDE.md is under 200 lines (ideally under 150)
2. Complex workflows converted to Agent Skills with proper SKILL.md files
3. All detailed reference content moved to docs
4. Clear "Skills Index" section (if skills created)
5. Clear "Reference Documents Index" section (if docs extracted)
6. No loss of information or guidance
7. Improved token efficiency (50-80% reduction)
8. Maintained prescriptive nature
9. Easy discoverability of skills and detailed content
10. Skills follow best practices: progressive disclosure, token optimization, security
