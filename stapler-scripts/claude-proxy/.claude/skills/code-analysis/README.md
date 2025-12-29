# Code Analysis Skill

Systematic code analysis using progressive discovery: from source to binary, from documentation to reverse engineering.

## Description

This skill enables Claude to systematically analyze code across multiple contexts:
- Clone and analyze git repositories
- Inspect JAR files and Java code
- Search documentation across web sources
- Reverse engineer binaries using best practices
- Find API endpoints and integration points

## Installation

**Project-wide** (shared with team):
```bash
# Already installed in this project at:
# .claude/skills/code-analysis/
```

**Personal** (available across all projects):
```bash
cp -r .claude/skills/code-analysis ~/.claude/skills/
```

## Usage

This skill is automatically discovered by Claude when relevant tasks are detected.

### Automatic Triggers

Claude will use this skill when you ask to:
- "Analyze this codebase..."
- "Find API endpoints in..."
- "What does this JAR do?"
- "Reverse engineer this binary..."
- "How does [library] work internally?"
- "Find the implementation of..."
- "Audit the security of..."

### Example Tasks

1. **Repository Analysis**
   ```
   Analyze the Spring Boot application at https://github.com/example/app
   ```

2. **JAR Inspection**
   ```
   Download the Kafka client JAR and find all consumer API methods
   ```

3. **Binary Analysis**
   ```
   Analyze /usr/local/bin/myapp and identify what it communicates with
   ```

4. **API Discovery**
   ```
   Clone the repo and find all REST endpoints with their HTTP methods
   ```

## Structure

```
code-analysis/
├── SKILL.md              # Core instructions (3,500 tokens)
├── README.md            # This file
└── scripts/             # Executable analysis tools
    ├── safe-clone.sh    # Safely clone repos to temp directories
    ├── jar-inspector.py # JAR file analysis tool
    └── binary-analyzer.sh # Binary executable analysis
```

## Scripts

### safe-clone.sh

Safely clone git repositories to isolated temporary directories.

```bash
# Basic usage
./scripts/safe-clone.sh https://github.com/user/repo

# Keep directory after analysis
./scripts/safe-clone.sh https://github.com/user/repo --keep

# Custom depth
./scripts/safe-clone.sh https://github.com/user/repo 5
```

**Features**:
- Timeout protection (60s default)
- URL validation
- Automatic cleanup
- Size reporting

### jar-inspector.py

Analyze JAR files and extract structured information.

```bash
# Basic analysis
./scripts/jar-inspector.py application.jar

# Full class listing
./scripts/jar-inspector.py application.jar --full

# Text output
./scripts/jar-inspector.py application.jar --output text

# Pipe to jq for filtering
./scripts/jar-inspector.py application.jar | jq '.api_patterns'
```

**Features**:
- Manifest parsing
- Class and package discovery
- Entry point detection
- Dependency extraction
- API pattern recognition
- Resource cataloging

### binary-analyzer.sh

Analyze binary executables safely.

```bash
# Basic analysis
./scripts/binary-analyzer.sh /usr/bin/myapp

# Text format
./scripts/binary-analyzer.sh myapp --output text

# More strings
./scripts/binary-analyzer.sh myapp --max-strings 1000

# Pipe to jq
./scripts/binary-analyzer.sh myapp | jq '.interesting'
```

**Features**:
- File type detection
- Symbol extraction
- Dependency listing
- String analysis
- URL/path discovery
- API pattern detection

## Security

✅ **All operations are read-only**
- Never executes analyzed code
- Isolated temp directories (`/tmp/analysis-*`)
- Timeout protection (60s default)
- Resource limits (100MB max downloads)
- Automatic cleanup on exit
- Input validation and sanitization

## Progressive Disclosure

The skill uses token-efficient progressive loading:

1. **Initial Load** (~3,500 tokens): Core SKILL.md with workflow and tools
2. **Context Loading** (as needed): Language-specific files loaded on-demand
3. **Script Execution**: Bundled scripts provide structured output

## Token Optimization

- **Core SKILL.md**: 3,500 tokens (JSON/table formats)
- **Typical session**: 4,500 tokens (core + one context file)
- **Maximum load**: 10,000 tokens (all files, rarely needed)

Achieved through:
- Structured formats (JSON) over prose
- Separate files for mutually exclusive contexts
- Inline script documentation (dual-purpose)
- Focused workflows with clear phases

## Workflow Phases

### 1. Source Discovery
- Clone repositories to temp directories
- Identify project type (Java, Python, Node.js, etc.)
- Scan for common patterns and entry points

### 2. Dependency Analysis
- Extract dependency information
- Analyze JAR files (Java)
- List npm packages (JavaScript)
- Inspect requirements (Python)

### 3. Documentation Search
- Search web for official documentation
- Extract inline documentation from code
- Find API specifications (OpenAPI, Swagger)

### 4. Reverse Engineering (if needed)
- Binary analysis with strings/symbols
- Decompilation (Java: CFR, Procyon)
- Disassembly (objdump, radare2)

## Integration

This skill integrates with:
- **java-api-discovery**: Delegates to this skill for detailed JAR analysis with javap
- **research-workflow**: Uses web search for documentation discovery
- **Brave Search MCP**: Web documentation search
- **read-website-fast MCP**: Documentation extraction

## Best Practices

1. **Progressive Discovery**: Start simple (grep/search), escalate to complex (decompile/RE)
2. **Cache Results**: Store analysis in JSON for reuse
3. **Fail Gracefully**: Try alternatives if one method fails
4. **Document Findings**: Create markdown summaries with code snippets
5. **Respect Limits**: Don't analyze files >100MB or repos >1GB

## Common Patterns

### Finding API Endpoints

```bash
# Spring Boot
grep -r "@RequestMapping\|@GetMapping\|@PostMapping"

# Flask/FastAPI
grep -r "@app.route\|@router"

# Express.js
grep -r "app.get\|app.post\|router."
```

### Analyzing JARs

```bash
# Quick inspection
./scripts/jar-inspector.py app.jar

# Find controllers
./scripts/jar-inspector.py app.jar | jq '.api_patterns.controllers'
```

### Binary Analysis

```bash
# Full analysis
./scripts/binary-analyzer.sh myapp

# Find URLs
./scripts/binary-analyzer.sh myapp | jq '.interesting.urls'
```

## Error Handling

| Error | Resolution |
|-------|------------|
| Git clone fails | Try `--depth=1`, then ZIP download |
| JAR corrupted | Use `jar tf` for basic listing |
| Binary stripped | Focus on strings and imports |
| No documentation | Aggressive code search + RE |
| Rate limited | Add delays, use cached results |

## Performance Metrics

Target performance:
- **Time to first insight**: <30 seconds
- **API coverage**: >80% of endpoints found
- **False positive rate**: <10%
- **Resource usage**: <100MB disk, <1GB RAM

## Version History

- **v1.0.0** (2025-12-29): Initial release
  - Core SKILL.md with 4-phase workflow
  - safe-clone.sh for repository cloning
  - jar-inspector.py for JAR analysis
  - binary-analyzer.sh for executable analysis
  - Security-first design with isolation

## Contributing

To improve this skill:

1. **Add language support**: Create new analysis patterns for other languages
2. **Enhance scripts**: Add more features to existing scripts
3. **Add context files**: Create language-specific analysis guides
4. **Improve patterns**: Add more API/security patterns to recognize
5. **Optimize tokens**: Find ways to reduce token usage further

## Related Skills

- **java-api-discovery**: Detailed Java API analysis using javap
- **research-workflow**: Web research and documentation discovery
- **prompt-engineering**: Creating and refining analysis patterns

## Additional Resources

- [Awesome Reversing - Software Reverse Engineering](https://github.com/ReversingID/Awesome-Reversing?tab=readme-ov-file#software-reverse-engineering)
- [JAR File Specification](https://docs.oracle.com/javase/8/docs/technotes/guides/jar/jar.html)
- [ELF Binary Format](https://en.wikipedia.org/wiki/Executable_and_Linkable_Format)
- [Ghidra Documentation](https://ghidra-sre.org/)
