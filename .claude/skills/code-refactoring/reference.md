# Code Refactoring Reference

## Advanced Patterns

### Annotation Migration (Field → Constructor Injection)

```bash
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

### Optional Return Types

```bash
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

### Spring Boot Constructor Injection

```bash
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

### Scoped Refactoring (Single File Test)

```bash
# Test on single file first
grit apply '<pattern>' --files 'src/main/java/path/File.java' --dry-run
```

### API Migration

```bash
grit apply '`$obj.oldApi($$$args)` => `$obj.newApi($$$args)`' --dry-run
```

## Kotlin-Specific Troubleshooting

### catch block transformation doesn't work in GritQL

GritQL's Kotlin support is expression-level only. `catch (e: Exception) { $body }` produces error 200 ("Could not find variable") or 0 matches because `catch_block` is a statement node in Kotlin's tree-sitter grammar, not an expression node.

**Alternatives:**

1. **Single location** → use `Edit` tool directly
2. **Many locations** → use `ast-grep` YAML rule:

```bash
# Find all catch(Exception) blocks missing CancellationException guard
sg --pattern 'catch ($e: Exception) { $$$body }' --lang kotlin kmp/src/
```

Write a `.grit/` YAML rule or Python script for bulk structural edits.

3. **Inline patterns** (one-liner try-catch) → also not matchable with GritQL; use grep + Edit.

### `where` clause returns 0 matches

`where { $var <: contains \`pattern\` }` parses without error in v0.1.1 but consistently returns 0 matches. This appears to be a bug in v0.1.1 with or without the stdlib symlink. Omit the `where` clause and verify the base pattern matches first; add guards via a Python post-processing script if needed.

### `grit init` fails with SSH auth error

```
Failed to clone repo getgrit/stdlib: authentication required but no callback set
```

The stdlib is already bundled in the npm package. Symlink it:

```bash
mkdir -p .grit
ln -sf /home/linuxbrew/.linuxbrew/lib/node_modules/@getgrit/cli/node_modules/.grit/.gritmodules .grit/.gritmodules
```

No Kotlin-specific patterns exist in the stdlib anyway (only Go, Java, JS, Python, Rust).

## Troubleshooting

### gritql not installed

```bash
brew install gritql
grit --version
```

### Unexpected changes in dry-run

```bash
# Test on single file
grit apply '<pattern>' --files 'path/to/File.java' --dry-run

# Narrow pattern scope - check for overly broad matches
```

### Build fails after refactoring

```bash
# Rollback
git reset --hard HEAD

# Apply incrementally with smaller scope
```

### Pattern not matching

```bash
# Search for actual usage
rg "ClassName" --type java

# Test pattern syntax against gritql documentation
```

### Formatting conflicts

```bash
# Apply formatting after refactoring
./gradlew spotlessApply

# Stage formatting separately if needed
git add -p
```

## Decision Criteria

### Use gritql when:
- ✅ Change affects multiple files
- ✅ Pattern matching requires AST understanding
- ✅ Need to avoid false positives (comments, strings)
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
