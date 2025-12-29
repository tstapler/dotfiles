---
name: code-analysis
description: "Analyze code systematically: clone repos, inspect JARs, search documentation, reverse-engineer binaries. Triggers: analyzing unknown codebases, finding API endpoints, understanding compiled code, security auditing."
---

# Code Analysis Skill

Systematic code analysis using progressive discovery: from source to binary, from documentation to reverse engineering.

## Analysis Workflow

### Phase 1: Source Discovery
```json
{
  "actions": [
    {"tool": "git", "action": "clone to /tmp/analysis-*", "depth": 1},
    {"tool": "find", "action": "identify project type", "indicators": ["pom.xml", "package.json", "Cargo.toml"]},
    {"tool": "grep", "action": "scan for patterns", "patterns": ["API", "endpoint", "route", "handler"]}
  ],
  "output": "project-summary.json"
}
```

### Phase 2: Dependency Analysis
```json
{
  "java": {"tool": "jar-inspector.py", "targets": ["*.jar", "lib/*"], "extract": ["manifest", "classes", "resources"]},
  "python": {"tool": "pip", "action": "download --no-deps", "analyze": ["setup.py", "requirements.txt"]},
  "javascript": {"tool": "npm", "action": "list --json", "depth": 2},
  "binary": {"tool": "ldd/otool", "action": "list dependencies"}
}
```

### Phase 3: Documentation Search
```json
{
  "strategies": [
    {"source": "web", "query": "[project] API documentation site:github.io"},
    {"source": "repo", "paths": ["docs/", "*.md", "examples/"]},
    {"source": "code", "patterns": ["@api", "@route", "swagger", "openapi"]}
  ]
}
```

### Phase 4: Reverse Engineering (if needed)
```json
{
  "binary_analysis": {
    "strings": {"min_length": 8, "encoding": ["ascii", "utf-16"]},
    "symbols": {"demangle": true, "filter": "public"},
    "disassembly": {"tool": "objdump", "sections": [".text", ".rodata"]}
  },
  "java_decompilation": {
    "tool": "cfr/procyon",
    "output": "decompiled/",
    "options": ["--comments", "--recover-type-hints"]
  }
}
```

## Tool Selection Matrix

| Scenario | Primary Tool | Fallback | Output Format |
|----------|-------------|----------|---------------|
| Git repo available | `git clone --depth=1` | Download ZIP | Local directory |
| JAR file | `jar-inspector.py` | `jar tf` | Class listing |
| Binary executable | `binary-analyzer.sh` | `strings + file` | Analysis report |
| No source access | Web search | Reverse engineering | Documentation links |
| API discovery | `grep -r "route\\|endpoint"` | AST parsing | Endpoint list |

## Security Checklist

**MANDATORY for all operations:**
- [ ] Use temp directory: `/tmp/analysis-$(uuidgen)`
- [ ] Validate URLs/paths: No `..` or absolute paths outside /tmp
- [ ] Set resource limits: `timeout 60s`, max 100MB downloads
- [ ] Never execute: Only static analysis
- [ ] Clean up: `trap 'rm -rf /tmp/analysis-*' EXIT`

## Output Formats

### Project Summary
```json
{
  "project": "name",
  "type": "java|python|javascript|binary",
  "structure": {
    "main_files": [],
    "dependencies": [],
    "entry_points": []
  },
  "apis": [
    {"path": "/api/v1/users", "method": "GET", "file": "UserController.java:42"}
  ],
  "security_notes": []
}
```

### Binary Analysis Report
```json
{
  "file": "binary_name",
  "type": "ELF|PE|Mach-O",
  "architecture": "x86_64",
  "symbols": ["exported_functions"],
  "strings": ["interesting_strings"],
  "dependencies": ["libname.so.1"],
  "entry_point": "0x1000"
}
```

## Script Integration

### Safe Clone
```bash
# scripts/safe-clone.sh
#!/bin/bash
TEMP_DIR="/tmp/analysis-$(uuidgen)"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"
timeout 60s git clone --depth=1 "$1" repo 2>&1
echo "$TEMP_DIR/repo"
```

### JAR Inspector
```python
# scripts/jar-inspector.py
#!/usr/bin/env python3
import zipfile, json, sys
jar = zipfile.ZipFile(sys.argv[1])
classes = [f for f in jar.namelist() if f.endswith('.class')]
manifest = jar.read('META-INF/MANIFEST.MF').decode('utf-8', errors='ignore') if 'META-INF/MANIFEST.MF' in jar.namelist() else ''
print(json.dumps({'classes': classes[:100], 'manifest': manifest[:1000]}))
```

## Language-Specific Strategies

**Load additional context when needed:**
- Java projects → Load `java-analysis.md`
- Binary files → Load `binary-analysis.md`
- Web API discovery → Load `web-discovery.md`

## Best Practices

1. **Progressive Discovery**: Start simple (clone, grep), escalate to complex (decompile, RE)
2. **Cache Results**: Store analysis in structured JSON for reuse
3. **Fail Gracefully**: If one method fails, try alternatives
4. **Document Findings**: Create markdown summary with code snippets
5. **Respect Limits**: Don't analyze files >100MB or repos >1GB

## Common Patterns

### Finding API Endpoints
```bash
# Quick scan for common patterns
grep -r "route\|endpoint\|api\|REST" --include="*.java" --include="*.py" --include="*.js"

# Java Spring
grep -r "@RequestMapping\|@GetMapping\|@PostMapping"

# Python Flask/FastAPI
grep -r "@app.route\|@router"

# Node.js Express
grep -r "app.get\|app.post\|router.get"
```

### Analyzing JARs
```bash
# Download and inspect
curl -L -o app.jar "https://example.com/app.jar"
python3 scripts/jar-inspector.py app.jar > jar-analysis.json

# Find specific classes
jar tf app.jar | grep -i controller
```

### Binary Inspection
```bash
# Basic analysis
file binary_name
strings -n 10 binary_name | head -100
nm -D binary_name | grep -i api

# Advanced with script
./scripts/binary-analyzer.sh binary_name > analysis.json
```

## Error Handling

| Error | Resolution |
|-------|------------|
| Git clone fails | Try --depth=1, then ZIP download |
| JAR corrupted | Use `jar tf` for basic listing |
| Binary stripped | Focus on strings and imports |
| No documentation | Aggressive code search + RE |
| Rate limited | Add delays, use cached results |

## Metrics

Track analysis effectiveness:
- Time to first insight: <30 seconds
- API coverage: >80% of endpoints found
- False positive rate: <10%
- Resource usage: <100MB disk, <1GB RAM