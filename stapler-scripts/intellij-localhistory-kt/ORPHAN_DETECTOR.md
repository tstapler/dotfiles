# OrphanDetector Documentation

## Overview

The `OrphanDetector` class analyzes IntelliJ's content storage to identify orphaned content - files that are no longer referenced by active files but still consume disk space. It provides confidence scoring to help determine which content can be safely cleaned up.

## Location

- **Source**: `src/main/kotlin/com/stapler/localhistory/analyzer/OrphanDetector.kt`
- **Tests**: `src/test/kotlin/com/stapler/localhistory/analyzer/OrphanDetectorTest.kt`

## Key Classes

### OrphanStatus

Sealed class representing the orphan status of content:

```kotlin
sealed class OrphanStatus {
    object Active : OrphanStatus()          // Definitely still in use
    object Orphaned : OrphanStatus()        // Definitely orphaned
    data class Uncertain(                   // Status unclear
        val confidence: Float,               // 0.0 to 1.0
        val reason: String
    ) : OrphanStatus()
}
```

### ContentReference

Data class representing a reference to content from LocalHistory:

```kotlin
data class ContentReference(
    val contentId: Int,
    val path: String?,
    val timestamp: Long?,
    val changeType: String?  // "ContentChange", "Delete", etc.
)
```

## Detection Heuristics

The OrphanDetector uses several heuristics to determine orphan status:

1. **No References** → High confidence orphan (90%)
   - Content with NO references in LocalHistory

2. **Delete-Only References** → Definite orphan (100%)
   - Content with only "Delete" type references

3. **Delete After Content Change** → Definite orphan (100%)
   - Last reference is a "Delete" that occurred after the last "ContentChange"

4. **Very Old References** → High confidence orphan (90%)
   - No references for >90 days

5. **Old References** → Medium confidence orphan (70%)
   - No references for 30-90 days

6. **Recent Activity** → Active (not orphan)
   - ContentChange references within last 7 days

## Command-Line Usage

The OrphanDetector is integrated into the main CLI tool with three commands:

### 1. Analyze Orphans

```bash
# Basic analysis (summary only)
./gradlew run --args="orphan-analyze"

# Detailed analysis with list of orphans
./gradlew run --args="orphan-analyze --detailed"

# Custom confidence threshold (default 0.7)
./gradlew run --args="orphan-analyze --detailed -m 0.5"

# Specify custom directories
./gradlew run --args="orphan-analyze -d /path/to/LocalHistory -c /path/to/caches"
```

Output example:
```
=== Orphan Analysis Report ===
Total content items: 33560
Reference map entries: 1234

Status breakdown:
  Active: 5432 (16.2%)
  Orphaned: 2341 (7.0%)
  Uncertain: 25787

Uncertain by confidence:
  High (>90%): 15234
  Medium (70-90%): 8765
  Low (<70%): 1788

Orphaned content by age:
  < 1 week: 234
  1-4 weeks: 567
  1-3 months: 890
  > 3 months: 650
```

### 2. Check Specific Content

```bash
# Check if a specific content ID is orphaned
./gradlew run --args="orphan-check 15029"
```

Output:
```
=== Orphan Details for Content ID 15029 ===
Status: Orphaned
References found: 2
Content size: 2804 bytes
Content hash: ac333d322383a77afb933926a8f4efa7bf295564
Compressed: false
Last referenced path: /src/main/java/MyClass.java
Last reference time: 2024-11-15T10:30:00

Reference history:
  2024-11-15T10:30:00: Delete - /src/main/java/MyClass.java
  2024-11-14T15:45:00: ContentChange - /src/main/java/MyClass.java
```

### 3. Find Cleanup Candidates

```bash
# Find high-confidence orphans for cleanup
./gradlew run --args="orphan-clean"

# With size estimation
./gradlew run --args="orphan-clean --estimate-size"

# Custom confidence threshold (default 0.9)
./gradlew run --args="orphan-clean -m 0.95"
```

Output:
```
Found 2341 orphaned content items with confidence >= 90.0%

Definite orphans (650 items):
----------------------------------------
  ID: 12345
    Last path: /old/deleted/file.txt
    Size: 4567 bytes
  ...

High confidence orphans (1691 items):
----------------------------------------
  ID: 23456
    Reason: No references for 120 days
    Last path: /temp/cache.dat
    Size: 8901 bytes
  ...

Total orphaned content size: 303 MB
```

## Programmatic Usage

```kotlin
import com.stapler.localhistory.analyzer.OrphanDetector
import java.nio.file.Paths

// Create detector
val detector = OrphanDetector(
    localHistoryDir = Paths.get("/path/to/LocalHistory"),
    cachesDir = Paths.get("/path/to/caches")
)

// Build reference map from LocalHistory
val referenceMap = detector.buildReferenceMap()

// Check specific content
val status = detector.checkOrphanStatus(contentId = 12345, referenceMap)
when (status) {
    is OrphanStatus.Active -> println("Content is active")
    is OrphanStatus.Orphaned -> println("Content is orphaned")
    is OrphanStatus.Uncertain -> {
        println("Uncertain: ${status.confidence * 100}% confidence")
        println("Reason: ${status.reason}")
    }
}

// Find all orphans with minimum confidence
val orphans = detector.findOrphanedContent(
    contentIds = listOf(1, 2, 3, 4, 5),
    minConfidence = 0.8f
)

// Get detailed analysis report
val report = detector.analyzeOrphanPatterns()
report.printSummary()

// Get details for specific content
val details = detector.getOrphanDetails(contentId = 12345)
details.printDetails()
```

## Integration with ContentScanner

The OrphanDetector works with content IDs from the ContentScanner:

```kotlin
// Get all content IDs from storage
val contentIds = ContentStorageReader.open(cachesDir).use { reader ->
    reader.listContentIds()
}

// Check orphan status for all content
val orphanCandidates = detector.findOrphanedContent(contentIds)

// Process orphans
for ((contentId, status) in orphanCandidates) {
    println("Content $contentId: $status")
}
```

## Performance Considerations

- **Reference Map Building**: Can take 10-30 seconds for large LocalHistory
- **Memory Usage**: Reference map uses ~100 bytes per reference
- **Scalability**: Tested with 30,000+ content items
- **Caching**: Reference map can be cached and reused for multiple queries

## Graceful Error Handling

The OrphanDetector handles various error conditions:

1. **Missing LocalHistory**: Returns empty reference map, marks all content as uncertain
2. **Corrupted Records**: Skips corrupted entries, continues processing
3. **Missing Content Storage**: Returns null for content details
4. **Invalid Content IDs**: Returns null or empty results

## Future Enhancements

Potential improvements for the OrphanDetector:

1. **Persistent Cache**: Cache reference map to disk for faster subsequent runs
2. **Incremental Updates**: Update reference map incrementally as LocalHistory changes
3. **Pattern Learning**: Machine learning to improve orphan detection accuracy
4. **Batch Cleanup**: Automated cleanup of high-confidence orphans
5. **Integration with IDE**: Plugin to show orphan status in IntelliJ UI
6. **Cross-Project Analysis**: Detect content shared between multiple projects