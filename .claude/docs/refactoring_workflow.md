# Intelligent Code Refactoring with AST-Based Tools

## Overview

For systematic, safe code refactoring, use AST-based tools like **gritql** (installed via `brew install gritql`) for targeted, validated transformations. These tools provide precision that simple text-based find/replace cannot match.

## When to Use AST-Based Refactoring Tools

### ✅ Use gritql or similar tools for:
- **Multi-file refactoring**: Renaming classes, methods, or variables across the codebase
- **API migration**: Updating framework versions or migrating between libraries
- **Pattern refactoring**: Converting inheritance to composition, introducing design patterns
- **Code modernization**: Applying language-specific idioms (Java 8+ features, Kotlin conventions)
- **Structural changes**: Reorganizing class hierarchies or extracting interfaces
- **Systematic transformations**: Any change requiring understanding of code structure, not just text

### ❌ Use Edit tool instead for:
- **Single-file, simple changes**: Quick fixes or adjustments in one location
- **Logic refactoring**: Changes requiring business context understanding
- **Non-code files**: YAML, JSON, Markdown, configuration files
- **Exploratory changes**: When you need to understand code before refactoring

## Core Refactoring Workflow

### 1. Pre-Flight Checks
Before starting any refactoring:

```bash
# Verify clean git state (no uncommitted changes)
git status

# Ensure you're on a feature branch
git checkout -b refactor/<description>

# Verify build is clean
./gradlew clean build

# Ensure tests pass (establish baseline)
./gradlew test
```

### 2. Preview Changes (Dry-Run)
**ALWAYS preview before applying changes:**

```bash
# Preview transformation without applying
grit apply 'OldClassName => NewClassName' --dry-run

# Save preview for review
grit apply '<pattern>' --dry-run > /tmp/refactor-preview.diff

# Review the preview carefully
less /tmp/refactor-preview.diff
```

### 3. Apply Transformation
Only after validation:

```bash
# Apply the refactoring
grit apply 'OldClassName => NewClassName'

# Format code immediately
./gradlew spotlessApply

# Stage formatting changes
git add -u
```

### 4. Verify Changes
**Mandatory verification after refactoring:**

```bash
# Compilation check
./gradlew compileJava compileKotlin

# Run full test suite
./gradlew test testIntegration

# Code quality checks
./gradlew pmdMain

# Review actual changes
git diff HEAD
```

### 5. Commit and Document
```bash
# Commit with descriptive message
git commit -m "refactor: rename OldClass to NewClass for clarity"

# Push to remote
git push origin refactor/<description>
```

## Common Refactoring Patterns

### Pattern 1: Renaming Classes
```bash
# Preview
grit apply 'class ServiceMetricsInventory' -> 'class MetricInventory' --dry-run

# Apply
grit apply 'class ServiceMetricsInventory' -> 'class MetricInventory'
```

### Pattern 2: Method Renaming
```bash
# Rename method across all callers
grit apply '`$obj.getMonitors($$$args)` => `$obj.getActiveMonitors($$$args)`' --dry-run

# Apply after review
grit apply '`$obj.getMonitors($$$args)` => `$obj.getActiveMonitors($$$args)`'
```

### Pattern 3: Annotation Migration
```bash
# Replace @Autowired with constructor injection
grit apply '
  class $ClassName {
    @Autowired
    private $Type $field;
  }
' => '
  class $ClassName {
    private final $Type $field;

    public $ClassName($Type $field) {
      this.$field = $field;
    }
  }
' --dry-run
```

### Pattern 4: API Migration
```bash
# Update deprecated API usage
grit apply '`$obj.oldMethod($$$args)` => `$obj.newMethod($$$args)`' --dry-run
```

## Integration with Existing Workflows

### Works Seamlessly With:
- **Git workflows**: Refactor on feature branches, easy rollback
- **Code quality tools**: Run spotlessApply, PMD checks after refactoring
- **Testing**: Verify behavior preservation with full test suite
- **CI/CD**: Same validation runs locally and in pipelines

### Maintains Tool Preferences:
- **Don't use bash for file operations**: gritql is a specialized refactoring tool, not a file operation
- **Use Edit for simple changes**: Reserve AST tools for complex structural changes
- **Follow project conventions**: Apply formatting and quality checks after refactoring

## Troubleshooting

### Common Issues

**Issue**: gritql not found
```bash
# Install via homebrew
brew install gritql

# Verify installation
grit --version
```

**Issue**: Unexpected changes in dry-run
```bash
# Review the pattern carefully
# Check for overly broad matches
# Test on a single file first
grit apply '<pattern>' --files 'src/main/java/path/to/File.java' --dry-run
```

**Issue**: Build fails after refactoring
```bash
# Rollback and try again
git reset --hard HEAD

# Apply more incrementally
# Focus on smaller scope first
```

## Decision Criteria: Tool Selection

### Use gritql when:
- ✅ Change affects multiple files
- ✅ Pattern matching requires AST understanding
- ✅ Need to avoid false positives (e.g., comments, strings)
- ✅ Want validation before applying
- ✅ Refactoring is systematic and repeatable

### Use Edit tool when:
- ✅ Single file, single change
- ✅ Change is context-dependent
- ✅ Logic requires understanding, not just structure
- ✅ Quick fix or adjustment

### Use MultiEdit when:
- ✅ Same simple change across multiple files
- ✅ Pattern is straightforward text replacement
- ✅ AST parsing would be overkill

## Project-Specific Examples

### Example 1: Removing Deprecated Model
```bash
# Search for usages
rg "ServiceMetricsInventory" --type java

# Preview removal and replacement
grit apply 'import bet.fanatics.scorecards.model.ServiceMetricsInventory' -> '' --dry-run

# Apply and verify
grit apply 'import bet.fanatics.scorecards.model.ServiceMetricsInventory' -> ''
./gradlew clean build
```

### Example 2: Modernizing Java Code
```bash
# Convert to Optional return types
grit apply '
  public $Type $method($$$params) {
    return null;
  }
' => '
  public Optional<$Type> $method($$$params) {
    return Optional.empty();
  }
' --dry-run
```

### Example 3: Spring Boot Best Practices
```bash
# Replace field injection with constructor injection
grit apply '
  @Service
  public class $ClassName {
    @Autowired
    private $Type $field;
  }
' => '
  @Service
  public class $ClassName {
    private final $Type $field;

    public $ClassName($Type $field) {
      this.$field = $field;
    }
  }
' --dry-run
```

## Quality Checklist

Before considering refactoring complete:

- [ ] **Preview reviewed**: Dry-run output examined for correctness
- [ ] **Changes applied**: Refactoring executed successfully
- [ ] **Code formatted**: spotlessApply run and committed
- [ ] **Compilation verified**: Clean build with no errors
- [ ] **Tests passing**: Full test suite execution successful
- [ ] **Code quality clean**: PMD analysis shows no new issues
- [ ] **Git diff reviewed**: All changes intentional and correct
- [ ] **Commit descriptive**: Clear explanation of refactoring rationale
- [ ] **Branch pushed**: Changes available for PR and review

## Integration with Agents

The `code-refactoring` agent incorporates these practices and will automatically use gritql when appropriate. Invoke it for systematic refactoring tasks:

```
@agent code-refactoring

Please refactor the ServiceMetricsInventory class to MetricInventory across the codebase
```

The agent will guide you through the complete workflow with proper validation at each step.
