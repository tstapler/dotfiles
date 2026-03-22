# IntelliJ LocalHistory API Facade Implementation Plan

## Executive Summary

This plan outlines the migration from custom LocalHistory parsing to using IntelliJ's official APIs, wrapped in a facade pattern. The custom parsing is failing with IntelliJ 2025's changed format, requiring a more robust solution using IntelliJ's own APIs.

## Problem Analysis

### Current State Issues
1. **Format Incompatibility**: Custom parsing shows "Unknown" change types in IntelliJ 2025
2. **Maintenance Burden**: Each IntelliJ version change potentially breaks parsing
3. **Incomplete Coverage**: Custom parser may miss nuanced data structures
4. **Reliability Concerns**: Reverse-engineered format is fragile

### Root Cause
- IntelliJ LocalHistory format changed between versions
- Binary format not documented publicly
- Custom VarInt/VarLong parsing doesn't match new encoding

## Requirements

### Functional Requirements

#### FR1: IntelliJ API Integration
- **FR1.1**: Research and identify IntelliJ LocalHistory API classes
- **FR1.2**: Add required IntelliJ dependencies to build.gradle.kts
- **FR1.3**: Create facade interface matching current functionality
- **FR1.4**: Implement facade using IntelliJ APIs

#### FR2: Data Access Capabilities
- **FR2.1**: Read change records with timestamps
- **FR2.2**: Retrieve file paths for changes
- **FR2.3**: Get change types (Create, Delete, Modify, etc.)
- **FR2.4**: Access content IDs for file versions
- **FR2.5**: Support project-level filtering

#### FR3: Backward Compatibility
- **FR3.1**: Maintain existing CLI command structure
- **FR3.2**: Preserve data structures (ChangeInfo, ChangeSetInfo, Record)
- **FR3.3**: Support same output formats

### Non-Functional Requirements

#### NFR1: Performance
- **NFR1.1**: Lazy loading of history data
- **NFR1.2**: Efficient memory usage for large histories
- **NFR1.3**: Response time < 2s for typical queries

#### NFR2: Reliability
- **NFR2.1**: Graceful handling of API changes
- **NFR2.2**: Version detection and compatibility checks
- **NFR2.3**: Clear error messages for unsupported versions

#### NFR3: Maintainability
- **NFR3.1**: Clear separation between facade and implementation
- **NFR3.2**: Comprehensive documentation of API usage
- **NFR3.3**: Unit tests for facade methods

## Architecture Design

### Component Architecture

```
┌─────────────────────────────────────────────────┐
│                 CLI Layer                       │
│         (Main.kt, Commands)                     │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│           LocalHistory Facade                   │
│      (LocalHistoryFacade interface)             │
├──────────────────────────────────────────────────┤
│ + getChangeSets(): List<ChangeSetInfo>         │
│ + searchFiles(term: String): List<ChangeInfo>   │
│ + getContentRecord(id: Int): ContentRecord?     │
│ + getRecentChanges(limit: Int): List<...>      │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│        Implementation Strategies                │
├──────────────────┬───────────────────────────────┤
│  IntelliJAPIImpl │        CustomParserImpl      │
│   (Primary)      │         (Fallback)           │
└──────────────────┴───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│          IntelliJ Platform APIs                 │
│  com.intellij.history.core.*                    │
│  com.intellij.history.integration.*             │
│  com.intellij.openapi.vfs.*                     │
└──────────────────────────────────────────────────┘
```

### Design Patterns

#### 1. Facade Pattern
```kotlin
interface LocalHistoryFacade {
    fun initialize(historyPath: Path, cachesPath: Path)
    fun getChangeSets(filter: ChangeFilter? = null): List<ChangeSetInfo>
    fun searchByPath(searchTerm: String): List<ChangeInfo>
    fun getContentById(contentId: Int): ContentRecord?
    fun close()
}
```

#### 2. Strategy Pattern for Implementation Selection
```kotlin
class LocalHistoryFacadeFactory {
    fun create(historyPath: Path): LocalHistoryFacade {
        return when {
            IntelliJAPIImpl.isSupported() -> IntelliJAPIImpl(historyPath)
            else -> CustomParserImpl(historyPath) // Fallback
        }
    }
}
```

#### 3. Adapter Pattern for Data Transformation
```kotlin
class IntelliJToModelAdapter {
    fun toChangeSetInfo(ideaChangeSet: Any): ChangeSetInfo
    fun toContentRecord(ideaContent: Any): ContentRecord
}
```

### Key API Research Findings

Based on research, the IntelliJ LocalHistory API includes:

#### Core Classes (Expected)
- `com.intellij.history.core.LocalHistoryFacade` - Main API entry point
- `com.intellij.history.core.changes.ChangeSet` - Change grouping
- `com.intellij.history.integration.LocalHistoryImpl` - Implementation
- `com.intellij.history.core.tree.Entry` - File/directory entries
- `com.intellij.history.core.Content` - File content storage

#### Required Dependencies
```kotlin
// build.gradle.kts additions
dependencies {
    // Core platform APIs
    implementation("com.jetbrains.intellij.platform:core:243.21565.208")
    implementation("com.jetbrains.intellij.platform:core-impl:243.21565.208")

    // LocalHistory (LVCS) implementation
    implementation("com.jetbrains.intellij.platform:lvcs-impl:243.21565.208")

    // Virtual File System
    implementation("com.jetbrains.intellij.platform:vfs:243.21565.208")

    // Required utilities
    implementation("com.jetbrains.intellij.platform:util:243.21565.208")
    implementation("com.jetbrains.intellij.platform:util-rt:243.21565.208")
}
```

## Implementation Plan

### Phase 1: Research & Dependency Setup (2-3 days)

#### 1.1 IntelliJ API Discovery
- [ ] Download IntelliJ Community source code
- [ ] Analyze `platform/lvcs-impl` module structure
- [ ] Document available API classes and methods
- [ ] Create API usage examples

#### 1.2 Dependency Configuration
- [ ] Update build.gradle.kts with required dependencies
- [ ] Resolve dependency conflicts
- [ ] Verify compilation with new dependencies
- [ ] Create minimal API test program

### Phase 2: Facade Design (2 days)

#### 2.1 Interface Definition
- [ ] Create `LocalHistoryFacade.kt` interface
- [ ] Define data models matching existing structures
- [ ] Create filter and query parameter classes
- [ ] Document interface contracts

#### 2.2 Factory Pattern Implementation
- [ ] Create `LocalHistoryFacadeFactory.kt`
- [ ] Implement version detection logic
- [ ] Add configuration for implementation selection
- [ ] Create logging for facade selection

### Phase 3: IntelliJ API Implementation (4-5 days)

#### 3.1 Core Implementation
- [ ] Create `IntelliJAPILocalHistoryImpl.kt`
- [ ] Implement initialization and connection
- [ ] Add change set retrieval methods
- [ ] Implement content access methods

#### 3.2 Data Transformation
- [ ] Create adapters for IntelliJ objects to models
- [ ] Handle null/missing data gracefully
- [ ] Implement filtering and searching
- [ ] Add pagination support

#### 3.3 Error Handling
- [ ] Add try-catch blocks for API calls
- [ ] Create custom exceptions for API failures
- [ ] Implement retry logic for transient errors
- [ ] Add fallback to custom parser

### Phase 4: Integration & Migration (3 days)

#### 4.1 Command Updates
- [ ] Update `Main.kt` to use facade
- [ ] Modify commands to use facade methods
- [ ] Preserve existing CLI behavior
- [ ] Add version info to `info` command

#### 4.2 Orphan Detector Migration
- [ ] Update `OrphanDetector.kt` to use facade
- [ ] Modify `buildReferenceMap()` method
- [ ] Test orphan detection with new implementation
- [ ] Verify performance characteristics

#### 4.3 Testing & Validation
- [ ] Create unit tests for facade
- [ ] Test with multiple IntelliJ versions
- [ ] Validate output consistency
- [ ] Performance benchmarking

### Phase 5: Documentation & Polish (1-2 days)

#### 5.1 Documentation
- [ ] Update README with new architecture
- [ ] Document API dependencies
- [ ] Create troubleshooting guide
- [ ] Add version compatibility matrix

#### 5.2 Error Messages & Logging
- [ ] Improve error messages
- [ ] Add debug logging options
- [ ] Create diagnostic commands
- [ ] Document common issues

## Known Issues & Mitigation

### Potential Bug: API Class Loading
**Issue**: IntelliJ APIs may require specific classloader configuration
**Mitigation**:
- Use reflection for initial class discovery
- Implement classloader isolation
- Add runtime detection of available APIs

### Potential Bug: Version Incompatibility
**Issue**: API changes between IntelliJ versions
**Mitigation**:
- Version detection at startup
- Multiple implementation strategies
- Graceful degradation to custom parser

### Potential Bug: Memory Leaks
**Issue**: IntelliJ APIs may hold references to large data structures
**Mitigation**:
- Implement proper resource cleanup
- Use weak references where appropriate
- Add memory monitoring

### Potential Bug: Concurrent Access
**Issue**: LocalHistory files may be locked by running IntelliJ
**Mitigation**:
- Read-only access mode
- File locking detection
- Retry with backoff strategy

## Testing Strategy

### Unit Tests
```kotlin
class LocalHistoryFacadeTest {
    @Test
    fun `should retrieve change sets`()
    @Test
    fun `should search by file path`()
    @Test
    fun `should handle missing content gracefully`()
    @Test
    fun `should detect IntelliJ version correctly`()
}
```

### Integration Tests
- Test with real LocalHistory data
- Verify cross-version compatibility
- Performance testing with large histories
- Memory usage profiling

### Acceptance Tests
- All existing CLI commands work
- Output format unchanged
- Performance meets requirements
- Error handling improved

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| IntelliJ APIs not available in Maven | Medium | High | Use IntelliJ Community source directly |
| API changes in future versions | High | Medium | Abstraction layer + version detection |
| Performance degradation | Low | Medium | Caching + lazy loading |
| Incomplete API documentation | High | Low | Source code analysis + experimentation |

## Success Criteria

1. **Functional**: All CLI commands work with IntelliJ 2025 LocalHistory
2. **Reliable**: No "Unknown" change types in output
3. **Performant**: Query response < 2 seconds
4. **Maintainable**: Clear separation of concerns
5. **Documented**: Complete API usage documentation

## Alternative Approaches Considered

### Alternative 1: JNI Bridge to IntelliJ
- **Pros**: Direct access to IntelliJ internals
- **Cons**: Complex setup, platform-specific

### Alternative 2: REST API Wrapper
- **Pros**: Language-agnostic, clean separation
- **Cons**: Requires running IntelliJ instance

### Alternative 3: Reverse Engineer New Format
- **Pros**: No dependencies, full control
- **Cons**: Fragile, high maintenance

## Conclusion

The facade pattern with IntelliJ API integration provides the most robust solution for reading LocalHistory data. This approach ensures compatibility with future IntelliJ versions while maintaining the existing CLI interface. The phased implementation allows for incremental progress with fallback options at each stage.

## Appendix A: Code Examples

### Example Facade Usage
```kotlin
val facade = LocalHistoryFacadeFactory.create(localHistoryDir)
facade.use { history ->
    // Get recent changes
    val changes = history.getChangeSets(
        ChangeFilter(limit = 100, afterDate = yesterday)
    )

    // Search for specific file
    val fileChanges = history.searchByPath("Main.java")

    // Retrieve content
    val content = history.getContentById(contentId)
}
```

### Example IntelliJ API Call (Hypothetical)
```kotlin
// Using IntelliJ's LocalHistory API
val localHistory = LocalHistoryImpl.getInstanceImpl()
val facade = localHistory.facade

val changeSets = facade.getChangeSets(
    facade.createChangeSetFilter()
        .withLimit(100)
        .build()
)
```

## Appendix B: Dependency Resolution Strategy

1. Try official JetBrains Maven repositories
2. Extract from IntelliJ Community distribution
3. Build from source if necessary
4. Create minimal shaded JAR with required classes
