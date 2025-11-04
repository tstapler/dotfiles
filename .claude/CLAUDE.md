# Enhanced Claude Project Instructions

## Automatic Activation

These instructions are automatically active for all conversations in this project. All available tools (Sequential Thinking, Brave Search, Puppeteer, REPL/Analysis, and Artifacts) should be utilised as needed without requiring explicit activation.

## Default Workflow

Every new conversation should automatically begin with Sequential Thinking to determine which other tools are needed for the task at hand.

## MANDATORY TOOL USAGE

- Sequential Thinking must be used for all multi-step problems or research tasks
- Brave Search must be used for any fact-finding or research queries
- Puppeteer must be used when web verification or deep diving into specific sites is needed
- REPL/Analysis must be used for any data processing or calculations
- Knowledge Graph should store important findings that might be relevant across conversations
- Artifacts must be created for all substantial code, visualizations, or long-form content

## Source Documentation Requirements

- All search results must include full URLs and titles
- Screenshots should include source URLs and timestamps
- Data sources must be clearly cited with access dates
- Knowledge Graph entries should maintain source links
- All findings should be traceable to original sources
- Brave Search results should preserve full citation metadata
- External content quotes must include direct source links

## Core Workflow

### 1. INITIAL ANALYSIS (Sequential Thinking)
- Break down the research query into core components
- Identify key concepts and relationships
- Plan search and verification strategy
- Determine which tools will be most effective

### 2. PRIMARY SEARCH (Brave Search)
- Start with broad context searches
- Use targeted follow-up searches for specific aspects
- Apply search parameters strategically (count, offset)
- Document and analyze search results

### 3. DEEP VERIFICATION (Puppeteer)
- Navigate to key websites identified in search
- Take screenshots of relevant content
- Extract specific data points
- Click through and explore relevant links
- Fill forms if needed for data gathering

### 4. DATA PROCESSING
- Use the analysis tool (REPL) for complex calculations
- Process any CSV files or structured data
- Create visualisations when helpful
- Store important findings in knowledge graph if persistent storage needed

### 5. SYNTHESIS & PRESENTATION
- Combine findings from all tools
- Present information in structured format
- Create artifacts for code, visualizations, or documents
- Highlight key insights and relationships

## Tool-Specific Guidelines

### BRAVE SEARCH
- **CRITICAL RATE LIMIT**: Brave Search has a 1 per second rate limit. NEVER make consecutive brave search calls - always either sleep 1+ seconds between calls OR run a different command in between
- Use count parameter for result volume control
- Apply offset for pagination when needed
- Combine multiple related searches
- Document search queries for reproducibility
- Include full URLs, titles, and descriptions in results
- Note search date and time for each query
- Track and cite all followed search paths
- Preserve metadata from search results

### PUPPETEER
- Take screenshots of key evidence
- Use selectors precisely for interaction
- Handle navigation errors gracefully
- Document URLs and interaction paths
- Always verify that you successfully arrived at the correct page, and received the information you were looking for, if not try again

### SEQUENTIAL THINKING
- Always break complex tasks into manageable steps
- Document thought process clearly
- Allow for revision and refinement
- Track branches and alternatives

### REPL/ANALYSIS
- Use for complex calculations
- Process and analyse data files
- Verify numerical results
- Document analysis steps

### ARTIFACTS
- Create for substantial code pieces
- Use for visualisations
- Document file operations
- Store long-form content

## Implementation Notes

- Tools should be used proactively without requiring user prompting
- Multiple tools can and should be used in parallel when appropriate
- Each step of analysis should be documented
- Complex tasks should automatically trigger the full workflow

## Python Development

- Always use `uv` for installing and manipulating python dependencies
- For complete Python coding standards, see `~/.claude/docs/python_standards.md`

## Git Guidelines

- Only push the specific branch that you're working on

## Code Editing

- Use the serena mcp server for editing and understanding code whenever possible (editing supported languages)

## Code Refactoring

For systematic, safe code refactoring with AST-based tools like gritql:
- See `~/.claude/docs/refactoring_workflow.md` for complete workflow
- Use for multi-file refactoring, API migrations, pattern changes
- Always preview with `--dry-run` before applying changes

## Infrastructure and Testing

For TestKube, PGBouncer, and Kubernetes-related testing:
- See `~/.claude/docs/infrastructure_testing.md` for complete procedures
- Always specify Kubernetes context explicitly
- Use proxy client mode for local TestKube CLI work

## Docker Development

For Docker build and test workflows:
- See `~/.claude/docs/docker_workflow.md` for complete procedures
- Always run `make validate` before pushing
- Use Makefile commands for consistent workflow

## Prompt Engineering

For advanced prompting techniques and best practices:
- See `~/.claude/docs/prompt_engineering.md` for comprehensive guide
- Apply XML tags for structure, multishot for examples, CoT for reasoning
- Focus on clear, explicit instructions with concrete success criteria

## Important Instruction Reminders

- Do what has been asked; nothing more, nothing less
- NEVER create files unless they're absolutely necessary for achieving your goal
- ALWAYS prefer editing an existing file to creating a new one
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User
- Always use the SUCCESS framework to guide your communication style

## Reference Documents Index

All detailed reference documentation is stored in `~/.claude/docs/`:

- **python_standards.md** - Complete Python coding guidelines and best practices
- **refactoring_workflow.md** - AST-based refactoring with gritql, complete workflow
- **infrastructure_testing.md** - TestKube, PGBouncer, Kubernetes testing procedures
- **docker_workflow.md** - Docker build, test, and validation workflows
- **prompt_engineering.md** - Advanced prompting techniques and patterns
