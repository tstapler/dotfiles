# Java API Discovery Reference

## Detailed javap Options

### Basic Options
```bash
javap [options] classfile

-cp <path>     # Classpath (JAR file location)
-s             # Print internal type signatures (shows generics)
-p             # Show private members
-c             # Disassemble bytecode
-v             # Verbose (all info)
-l             # Line and local variable tables
```

### Practical Combinations

```bash
# Quick public API view
javap -cp lib.jar com.example.Class

# Full signatures with generics
javap -s -cp lib.jar com.example.Class

# Everything including private
javap -p -cp lib.jar com.example.Class

# Full disassembly (when you need implementation details)
javap -c -v -cp lib.jar com.example.Class
```

## Real-World Discovery Examples

### Example 1: Datadog API Pagination

**Problem**: Assumed cursor-based pagination existed

**Discovery**:
```bash
javap -cp datadog-api-client.jar \
  com.datadog.api.client.v2.api.DowntimesApi | grep -i page

# Output:
# public DowntimesApi.ListDowntimesOptionalParameters pageOffset(java.lang.Long)
# public DowntimesApi.ListDowntimesOptionalParameters pageLimit(java.lang.Long)
```

**Solution**: Use offset-based pagination, not cursor

### Example 2: Union Type Response

**Problem**: Tried to access schedule fields directly

**Discovery**:
```bash
javap -cp datadog-api-client.jar \
  com.datadog.api.client.v2.model.DowntimeScheduleResponse

# Output:
# public java.lang.Object getActualInstance()
# public com.datadog.api.client.v2.model.DowntimeScheduleRecurrencesResponse ...
# public com.datadog.api.client.v2.model.DowntimeScheduleOneTimeResponse ...
```

**Solution**:
```java
Object actual = schedule.getActualInstance();
if (actual instanceof DowntimeScheduleRecurrencesResponse) {
    DowntimeScheduleRecurrencesResponse recurring =
        (DowntimeScheduleRecurrencesResponse) actual;
}
```

### Example 3: Missing Fields

**Problem**: Assumed createdBy field existed

**Discovery**:
```bash
javap -cp datadog-api-client.jar \
  com.datadog.api.client.v2.model.DowntimeResponseData | grep -i created

# Output: (nothing - field doesn't exist)
```

**Solution**: Remove field from model, use only available fields

### Example 4: Enum Constants

**Problem**: Used wrong constant name (LEFT_PAREN vs LPAREN)

**Discovery**:
```bash
javap -cp parser.jar com.example.TokenType | grep PAREN

# Output:
# public static final com.example.TokenType LPAREN
# public static final com.example.TokenType RPAREN
```

**Solution**: Use correct constant names

### Example 5: Collection Types

**Problem**: Expected `Set<String>` but got `List<String>`

**Discovery**:
```bash
javap -s -cp lib.jar com.example.Monitor | grep -A1 getTags

# Output:
# public java.util.List getTags();
#   descriptor: ()Ljava/util/List;
```

**Solution**: Change variable type to `List<String>`

## Multi-JAR Discovery

### Finding Classes Across Dependencies

```bash
# Search all JARs in Gradle cache for a class
for jar in $(find ~/.gradle/caches -name "*.jar" -type f); do
  if jar tf "$jar" 2>/dev/null | grep -q "ClassName"; then
    echo "Found in: $jar"
  fi
done
```

### Examining Transitive Dependencies

```bash
# List project dependencies
./gradlew dependencies --configuration runtimeClasspath

# Find specific dependency version
./gradlew dependencies | grep "library-name"
```

## Troubleshooting

### Class Not Found

```bash
# Verify class exists in JAR
jar tf lib.jar | grep -i "ClassName"

# Check exact package path
jar tf lib.jar | grep "ClassName" | head -1
# Use full path: com/example/sub/ClassName.class → com.example.sub.ClassName
```

### No Output from javap

```bash
# Ensure using dots not slashes for class name
# Wrong: javap com/example/Class
# Right: javap com.example.Class

# Verify JAR is on classpath
javap -cp /full/path/to/lib.jar com.example.Class
```

### Generics Not Showing

```bash
# Use -s flag for type signatures
javap -s -cp lib.jar com.example.Class

# Or -v for maximum detail
javap -v -cp lib.jar com.example.Class
```

## Integration with IDE

### IntelliJ IDEA
1. Navigate to External Libraries
2. Find JAR → Right-click → Open in Terminal
3. Run javap commands

### VS Code
1. Use Java extension's "Go to Definition" first
2. Fall back to javap for compiled-only classes

### Command Line Workflow
```bash
# Quick alias for common operations
alias japi='javap -cp'

# Usage
japi ~/.gradle/caches/.../lib.jar com.example.Class
```
