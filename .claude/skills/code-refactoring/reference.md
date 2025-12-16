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
