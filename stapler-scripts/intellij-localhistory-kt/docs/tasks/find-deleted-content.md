# Find Deleted Content Feature

## Overview

This feature enables users to discover content they may have accidentally deleted from IntelliJ's LocalHistory and PersistentFS content storage. It provides a discovery mode that helps users explore what was deleted without knowing exact file names, with output optimized for analysis by Claude or other LLMs.

## Context

The intellij-localhistory-kt CLI tool currently has:
- A working `ContentStorage.kt` parser that reads from IntelliJ's `content.dat` (AppendOnlyLog format)
- A `recover` command that depends on LocalHistory parsing (has issues with newer IntelliJ formats)
- Access to 33,000+ content records with both text and binary files
- Support for compressed (LZ4) and uncompressed content

## Architecture Decision Records

### ADR-001: Dual-Source Content Discovery

**Decision**: Implement content discovery using both LocalHistory changes and PersistentFS content storage.

**Rationale**: 
- LocalHistory provides temporal context and file paths for deletions
- PersistentFS contains actual content that may not have LocalHistory entries
- Combined approach maximizes recovery potential

**Consequences**:
- More complex implementation but better coverage
- Need to handle format incompatibilities gracefully
- Can correlate deletion events with orphaned content

### ADR-002: Content-First Discovery Pattern

**Decision**: Use content characteristics (text patterns, file signatures) rather than file paths as primary discovery mechanism.

**Rationale**:
- Users often don't remember exact file names of deleted content
- Content patterns are more memorable (e.g., "that SQL query about users")
- Binary file signatures can identify file types without extensions

**Consequences**:
- Need robust content analysis and classification
- Higher computational cost for scanning
- Better user experience for recovery scenarios

### ADR-003: LLM-Optimized Output Format

**Decision**: Structure output as markdown with semantic sections and metadata for LLM analysis.

**Rationale**:
- LLMs can better understand structured markdown
- Metadata helps with pattern recognition
- Enables automated analysis of deletion patterns

**Consequences**:
- Standardized output format across commands
- Easy integration with Claude or other analysis tools
- Machine-readable while remaining human-friendly

## Requirements

### Functional Requirements

1. **Content Discovery**
   - Scan all content records in PersistentFS storage
   - Identify orphaned content (content without active file references)
   - Search content by text patterns, not just file names
   - Detect file types from content signatures

2. **Filtering Capabilities**
   - Filter by content type (text vs binary)
   - Filter by size ranges
   - Filter by estimated deletion time (if available)
   - Filter by file type signatures

3. **Content Preview**
   - Show snippets of text content
   - Display file type for binary content
   - Show content metadata (size, hash, compression)

4. **Analysis Export**
   - Export findings in LLM-friendly markdown format
   - Include deletion patterns and statistics
   - Generate content similarity groups

### Non-Functional Requirements

1. **Performance**
   - Scan 33,000+ records in under 10 seconds
   - Use lazy loading for content preview
   - Implement progress indicators for long operations

2. **Reliability**
   - Handle corrupted content gracefully
   - Support both legacy and modern storage formats
   - Provide fallback mechanisms for parsing failures

3. **Usability**
   - Clear, actionable output messages
   - Intuitive command-line interface
   - Helpful error messages with recovery suggestions

## Known Issues and Mitigation

### 🐛 Memory Exhaustion with Large Content Scans [SEVERITY: High]

**Description**: Loading all 33,000+ content records into memory simultaneously may cause OOM errors.

**Mitigation**:
- Implement streaming/pagination for content iteration
- Use memory-mapped files for large content
- Add --limit flag to restrict scan size
- Monitor memory usage and warn user

**Prevention Strategy**:
- Design with lazy evaluation by default
- Stream content records one at a time
- Cache only metadata, not full content

### 🐛 Corrupted Content Decompression Failures [SEVERITY: Medium]

**Description**: LZ4 decompression may fail on corrupted or partially written content.

**Mitigation**:
- Wrap decompression in try-catch blocks
- Mark corrupted content but continue scanning
- Log corruption details for debugging
- Provide raw content access option

**Prevention Strategy**:
- Validate content checksums before decompression
- Implement multiple decompression algorithms as fallback
- Add --skip-corrupted flag

### 🐛 False Positives in Orphan Detection [SEVERITY: Medium]

**Description**: Content may appear orphaned but still be referenced by active files.

**Mitigation**:
- Cross-reference with VFS records if available
- Mark confidence levels for orphan status
- Provide verification command
- Allow user to override orphan detection

**Prevention Strategy**:
- Build comprehensive reference map
- Use multiple detection heuristics
- Conservative approach: mark as "possibly orphaned"

## Implementation Tasks

### Phase 1: Foundation [Priority: Critical]

#### Task 1.1: Create ContentScanner Class
**File**: `src/main/kotlin/com/stapler/localhistory/scanner/ContentScanner.kt`

```kotlin
class ContentScanner(
    private val contentReader: ContentStorageReader,
    private val config: ScanConfig = ScanConfig()
) {
    fun scanAll(): Sequence<ContentScanResult>
    fun scanOrphaned(): Sequence<ContentScanResult>
    fun scanByPattern(pattern: Regex): Sequence<ContentScanResult>
}

data class ScanConfig(
    val maxMemoryMB: Int = 512,
    val enableCaching: Boolean = true,
    val skipCorrupted: Boolean = true
)

data class ContentScanResult(
    val contentId: Int,
    val metadata: ContentMetadata,
    val orphanStatus: OrphanStatus,
    val preview: String?
)
```

**Acceptance Criteria**:
- Implements memory-efficient streaming
- Handles both storage formats
- Provides progress callback mechanism
- Gracefully handles corrupted content

#### Task 1.2: Implement Content Classification
**File**: `src/main/kotlin/com/stapler/localhistory/analyzer/ContentClassifier.kt`

```kotlin
class ContentClassifier {
    fun classifyContent(content: ByteArray): ContentType
    fun detectFileType(content: ByteArray): FileType?
    fun extractTextPreview(content: ByteArray, maxLength: Int = 500): String?
    fun calculateSimilarityHash(content: ByteArray): String
}

sealed class ContentType {
    object Text : ContentType()
    object Binary : ContentType()
    data class Structured(val format: String) : ContentType() // JSON, XML, etc.
}
```

**Acceptance Criteria**:
- Detects common file signatures (PDF, ZIP, images, etc.)
- Identifies text encoding (UTF-8, ASCII, etc.)
- Extracts meaningful previews from text
- Generates similarity hashes for grouping

#### Task 1.3: Build Orphan Detection Logic
**File**: `src/main/kotlin/com/stapler/localhistory/analyzer/OrphanDetector.kt`

```kotlin
class OrphanDetector(
    private val localHistoryDir: Path,
    private val cachesDir: Path
) {
    fun buildReferenceMap(): ContentReferenceMap
    fun isOrphaned(contentId: Int): OrphanStatus
    fun findReferences(contentId: Int): List<FileReference>
}

sealed class OrphanStatus {
    object Active : OrphanStatus()
    object Orphaned : OrphanStatus()
    data class Uncertain(val confidence: Float) : OrphanStatus()
}
```

**Acceptance Criteria**:
- Parses VFS records for active references
- Correlates with LocalHistory changes
- Provides confidence scoring
- Caches reference map for performance

### Phase 2: Discovery Commands [Priority: High]

#### Task 2.1: Implement find-deleted Command
**File**: Update `src/main/kotlin/com/stapler/localhistory/Main.kt`

```kotlin
class FindDeletedCommand : CliktCommand(
    name = "find-deleted",
    help = "Discover potentially deleted content without knowing file names"
) {
    private val pattern by option("--pattern", "-p")
    private val type by option("--type", "-t").choice("text", "binary", "all")
    private val minSize by option("--min-size").int()
    private val maxSize by option("--max-size").int()
    private val limit by option("--limit", "-n").int().default(100)
    private val outputFormat by option("--format", "-f").choice("human", "markdown", "json")
    
    override fun run() {
        // Implementation
    }
}
```

**Acceptance Criteria**:
- Searches content by pattern, not filename
- Filters by type, size, and other criteria
- Shows preview snippets
- Outputs in multiple formats

#### Task 2.2: Create scan-orphans Command
**File**: Update `src/main/kotlin/com/stapler/localhistory/Main.kt`

```kotlin
class ScanOrphansCommand : CliktCommand(
    name = "scan-orphans",
    help = "Find orphaned content that may represent deleted files"
) {
    private val confidence by option("--confidence", "-c").float().default(0.7f)
    private val groupSimilar by option("--group-similar").flag()
    private val showReferences by option("--show-refs").flag()
    
    override fun run() {
        // Implementation
    }
}
```

**Acceptance Criteria**:
- Identifies orphaned content with confidence scores
- Groups similar content together
- Shows any remaining references
- Provides recovery suggestions

#### Task 2.3: Add analyze-patterns Command
**File**: Update `src/main/kotlin/com/stapler/localhistory/Main.kt`

```kotlin
class AnalyzePatternsCommand : CliktCommand(
    name = "analyze-patterns",
    help = "Analyze deletion patterns for LLM analysis"
) {
    private val days by option("--days", "-d").int().default(30)
    private val outputFile by option("--output", "-o").path()
    private val includeContent by option("--include-content").flag()
    
    override fun run() {
        // Implementation
    }
}
```

**Acceptance Criteria**:
- Generates deletion timeline
- Identifies bulk deletion events
- Correlates deletions with content types
- Outputs LLM-optimized markdown report

### Phase 3: Export and Analysis [Priority: Medium]

#### Task 3.1: Implement LLM Export Formatter
**File**: `src/main/kotlin/com/stapler/localhistory/export/LLMExporter.kt`

```kotlin
class LLMExporter {
    fun exportFindings(
        results: List<ContentScanResult>,
        format: ExportFormat = ExportFormat.Markdown
    ): String
    
    fun generateAnalysisPrompt(results: List<ContentScanResult>): String
    
    fun createRecoveryScript(results: List<ContentScanResult>): String
}

enum class ExportFormat {
    Markdown, JSON, CSV
}
```

**Acceptance Criteria**:
- Generates structured markdown with metadata
- Includes analysis prompts for Claude
- Creates executable recovery scripts
- Handles large result sets efficiently

#### Task 3.2: Build Content Similarity Analyzer
**File**: `src/main/kotlin/com/stapler/localhistory/analyzer/SimilarityAnalyzer.kt`

```kotlin
class SimilarityAnalyzer {
    fun groupBySimilarity(
        results: List<ContentScanResult>,
        threshold: Float = 0.8f
    ): List<SimilarityGroup>
    
    fun findDuplicates(results: List<ContentScanResult>): List<DuplicateGroup>
    
    fun detectPatterns(results: List<ContentScanResult>): List<ContentPattern>
}

data class SimilarityGroup(
    val representative: ContentScanResult,
    val members: List<ContentScanResult>,
    val similarity: Float
)
```

**Acceptance Criteria**:
- Groups similar content using fuzzy hashing
- Identifies exact duplicates
- Detects patterns in content (e.g., test files, configs)
- Provides similarity scores

#### Task 3.3: Create Interactive Recovery Wizard
**File**: `src/main/kotlin/com/stapler/localhistory/recovery/RecoveryWizard.kt`

```kotlin
class RecoveryWizard(
    private val scanner: ContentScanner,
    private val exporter: LLMExporter
) {
    fun startInteractive(): RecoverySession
    fun previewContent(contentId: Int): String
    fun recoverContent(contentId: Int, outputPath: Path): Boolean
    fun batchRecover(contentIds: List<Int>, outputDir: Path): RecoveryReport
}

data class RecoveryReport(
    val successful: Int,
    val failed: List<RecoveryFailure>,
    val outputPaths: List<Path>
)
```

**Acceptance Criteria**:
- Provides interactive content browsing
- Shows preview before recovery
- Supports batch recovery operations
- Generates recovery report

### Phase 4: Performance Optimization [Priority: Low]

#### Task 4.1: Implement Content Index Cache
**File**: `src/main/kotlin/com/stapler/localhistory/cache/ContentIndexCache.kt`

```kotlin
class ContentIndexCache(
    private val cacheDir: Path = Path.of(System.getProperty("user.home"), ".intellij-localhistory-cache")
) {
    fun buildIndex(contentReader: ContentStorageReader): ContentIndex
    fun loadIndex(): ContentIndex?
    fun updateIndex(changes: List<IndexChange>)
    fun invalidate()
}

data class ContentIndex(
    val version: Int,
    val createdAt: Instant,
    val entries: Map<Int, IndexEntry>
)
```

**Acceptance Criteria**:
- Caches content metadata for fast searches
- Detects storage changes and invalidates
- Supports incremental updates
- Provides significant speedup for repeated scans

#### Task 4.2: Add Parallel Processing Support
**File**: `src/main/kotlin/com/stapler/localhistory/scanner/ParallelScanner.kt`

```kotlin
class ParallelScanner(
    private val contentReader: ContentStorageReader,
    private val parallelism: Int = Runtime.getRuntime().availableProcessors()
) {
    fun scanInParallel(
        predicate: (ContentRecord) -> Boolean
    ): Flow<ContentScanResult>
    
    fun processChunked(
        chunkSize: Int = 1000,
        processor: (List<ContentRecord>) -> Unit
    )
}
```

**Acceptance Criteria**:
- Uses Kotlin coroutines for parallel processing
- Maintains order for deterministic results
- Handles backpressure appropriately
- Provides 3-5x speedup on multi-core systems

## Testing Strategy

### Unit Tests
- ContentScanner streaming and memory management
- ContentClassifier file type detection accuracy
- OrphanDetector reference correlation logic
- LLMExporter format generation

### Integration Tests
- Full scan with real IntelliJ cache data
- Recovery workflow end-to-end
- Format compatibility (legacy vs modern)
- Large dataset performance

### Performance Tests
- Memory usage under 512MB for 50,000 records
- Scan time under 10 seconds for full cache
- Export generation under 2 seconds

## Success Criteria

1. **Discovery Success**: Users can find deleted content using partial text patterns
2. **Recovery Rate**: 90%+ of orphaned content can be successfully recovered
3. **Performance**: Full scan completes in under 10 seconds for typical cache
4. **LLM Integration**: Output can be directly analyzed by Claude for patterns
5. **User Satisfaction**: Clear, actionable results without requiring IntelliJ internals knowledge

## Example Usage

```bash
# Find deleted content containing specific text
$ intellij-localhistory find-deleted --pattern "class UserService" --type text

# Scan for orphaned content with high confidence
$ intellij-localhistory scan-orphans --confidence 0.9 --group-similar

# Analyze deletion patterns for the last 30 days
$ intellij-localhistory analyze-patterns --days 30 --output report.md

# Export findings for Claude analysis
$ intellij-localhistory find-deleted --format markdown | pbcopy
# Then paste into Claude for analysis
```

## LLM Analysis Prompt Template

When exporting for LLM analysis, include this prompt template:

```markdown
# IntelliJ Deleted Content Analysis

## Content Summary
- Total orphaned records: {count}
- Date range: {start_date} to {end_date}
- Content types: {type_distribution}

## Deletion Patterns
{deletion_timeline}

## Orphaned Content Samples
{content_previews}

## Analysis Request
Please analyze these deletion patterns and identify:
1. Potential accidental deletions (important code/configs)
2. Bulk deletion events that might indicate mistakes
3. Patterns suggesting refactoring or project restructuring
4. High-value content that should be recovered

## Recovery Priority
Based on the content, please suggest recovery priority for the orphaned files.
```
