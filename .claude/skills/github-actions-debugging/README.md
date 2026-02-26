# GitHub Actions Debugging Skill

Debug GitHub Actions workflow failures by analyzing logs, identifying error patterns, and providing actionable solutions.

## Installation

This skill is automatically discovered by OpenCode/Claude from `~/.claude/skills/`.

**Verify installation:**
```bash
ls ~/.claude/skills/github-actions-debugging/
```

Should show:
- `SKILL.md` - Core debugging instructions
- `error-patterns.md` - Comprehensive error database
- `examples.md` - Step-by-step debugging walkthroughs
- `scripts/` - Executable tools
- `resources/` - Machine-readable data
- `README.md` - This file

## Usage

This skill is automatically loaded by Claude when debugging GitHub Actions failures.

**Triggers:**
- Workflow failures
- Job timeouts
- CI/CD errors
- Action failures
- Runner errors
- Log analysis requests

**Example tasks:**
- "Debug this GitHub Actions workflow failure"
- "Why is my CI build timing out?"
- "Fix the permission error in my workflow"
- "Analyze these workflow logs and identify the root cause"

## Structure

### Core Files

**`SKILL.md`** (3,500 tokens)
- 5-phase debugging methodology
- Quick reference table of 20 most common errors
- Tool selection guidance
- Output format requirements
- Integration with other skills/agents

**`error-patterns.md`** (2,000 tokens)
- Comprehensive database of 100+ error patterns
- Categorized by: Syntax, Dependency, Environment, Permission, Timeout, Network, Docker
- Each pattern includes: signature, causes, fixes, prevention

**`examples.md`** (1,500 tokens)
- 7 complete debugging walkthroughs
- Real-world scenarios with solutions
- Demonstrates systematic methodology

### Scripts

**`scripts/parse_workflow_logs.py`** (600 tokens)
- Automated log parser for large files (>500 lines)
- Extracts errors, categorizes, suggests fixes
- Outputs structured JSON report
- Dual-purpose: executable + documentation

**Usage:**
```bash
# Parse log file
python scripts/parse_workflow_logs.py workflow.log

# Parse from stdin
gh run view 12345 --log | python scripts/parse_workflow_logs.py

# Output format
{
  "summary": {
    "total_errors": 3,
    "categories": {"dependency": 2, "timeout": 1},
    "critical_count": 2
  },
  "errors": [...]
}
```

### Resources

**`resources/error-patterns.json`** (400 tokens)
- Machine-readable error pattern database
- Used for programmatic error matching
- JSON format for easy parsing

## Token Efficiency

The skill uses progressive disclosure:

| Load Level | Tokens | When Loaded |
|------------|--------|-------------|
| Metadata | 50 | Always (auto-discovery) |
| Core SKILL.md | 3,500 | When skill activated |
| error-patterns.md | 2,000 | Unknown errors |
| examples.md | 1,500 | Complex scenarios |
| Scripts | 600 | Large log files |
| Resources | 400 | Programmatic matching |

**Typical usage:** 3,500-5,500 tokens (core + 1-2 additional files)

## Security

✅ **No hardcoded secrets** - All scripts use environment variables
✅ **Input sanitization** - Safe regex and file handling
✅ **Read-only operations** - No file modifications by default
✅ **No external connections** - Operates on local files only

## Error Categories

The skill categorizes errors into:

- **Syntax** - YAML errors, invalid workflow configuration
- **Dependency** - npm, pip, go, cargo dependency issues
- **Environment** - Missing tools, files, configuration
- **Permission** - Token scopes, SSH keys, SAML SSO
- **Timeout** - Job timeouts, OOM kills
- **Network** - DNS, rate limiting, service outages
- **Docker** - Build failures, image issues

## Integration

**Works with existing skills/agents:**
- `github-pr` - PR workflows and status checks
- `github-debugger` - Specialized debugging beyond logs

**Delegates to github-pr when:**
- Failure related to PR workflow
- Need to analyze PR comments
- CI check is part of broader PR debugging

**Delegates to github-debugger when:**
- Application-level errors vs. CI/CD errors
- Complex multi-repo scenarios

## Version History

- **v1.0.0** (2026-01-04): Initial release
  - 5-phase debugging methodology
  - 20+ common error patterns
  - 100+ comprehensive error database
  - 7 example walkthroughs
  - Python log parser script
  - JSON error pattern database

## Contributing

Improvements welcome! Common contributions:

- **New error patterns** - Add to `error-patterns.md` and `resources/error-patterns.json`
- **Example scenarios** - Add to `examples.md`
- **Script enhancements** - Improve `parse_workflow_logs.py`
- **Documentation** - Clarify instructions in `SKILL.md`

## License

Part of Claude skills collection - use freely in your projects.

## Resources

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Runner Images**: https://github.com/actions/runner-images
- **Community Forum**: https://github.community/c/code-to-cloud/github-actions/41
