# PersistentFS Content Extraction Feature Plan

## Executive Summary

Implement support for extracting actual file content from IntelliJ's PersistentFS storage system to enable recovery of accidentally deleted files and analysis of deletion patterns. This feature will bridge the gap between LocalHistory records (which contain metadata and content IDs) and the actual file content stored in the PersistentFS `content.dat` file.

## Problem Statement

Currently, the IntelliJ LocalHistory tool can:
- Parse LocalHistory records to find file paths and change types
- Identify when files were modified or deleted
- Extract content IDs from ContentChange records

However, it **cannot**:
- Retrieve the actual file content associated with content IDs
- Show the contents of deleted files
- Help users recover accidentally deleted code
- Analyze what was lost in large deletions

The missing piece is the ability to read content from IntelliJ's PersistentFS storage system, specifically the `content.dat` file located in `~/Library/Caches/JetBrains/IntelliJIdea*/caches/`.

## Technical Context

### PersistentFS Storage Architecture

IntelliJ's PersistentFS uses a sophisticated multi-file storage system:

1. **LocalHistory Storage** (already parsed):
   - `changes.storageRecordIndex` - Index of change records
   - `changes.storageData` - Serialized ChangeSet objects containing content IDs

2. **PersistentFS Content Storage** (needs implementation):
   - `content.dat` - Actual file content stored by content ID
   - `content.dat.hashToId` - Hash-to-ID mapping for deduplication
   - `records.dat` - Virtual file system records
   - `attributes.dat` - File attributes storage

### Key Discoveries from Research

1. **Content Storage Model**:
   - Content is stored with reference counting (RefCountingContentStorage)
   - Each content piece has a unique integer ID
   - Content is deduplicated using content hashing
   - Page-based storage with 8KB default page size

2. **StoredContent Class**:
   - References content by integer ID
   - Uses `PersistentFS.contentsToByteArray(contentId)` to retrieve content
   - Implements reference counting for garbage collection

3. **AbstractStorage Pattern**:
   - Uses paired files: `.storageRecordIndex` and `.storageData`
   - Implements page-based storage with DataTable
   - Supports variable-length records with dynamic allocation

## Functional Requirements

### Core Features

1. **Content Retrieval by ID**
   - Input: Content ID from LocalHistory ContentChange record
   - Output: Raw byte array of file content
   - Error handling for missing/corrupted content

2. **Content Display**
   - Convert byte arrays to text with encoding detection
   - Handle binary files gracefully
   - Provide content preview with truncation for large files

3. **File Recovery**
   - Export recovered content to files
   - Preserve original file names and paths
   - Support batch recovery of multiple files

4. **Deletion Analysis**
   - List all deleted files with timestamps
   - Show size of deleted content
   - Identify patterns in deletions (e.g., entire directories)

### User Stories

```gherkin
Feature: Recover Deleted File Content

Scenario: User recovers accidentally deleted source file
  Given a file "UserService.java" was deleted yesterday
  When the user searches for "UserService"
  And selects the ContentChange record
  Then the tool displays the full source code
  And offers to save it to a new file

Scenario: User analyzes large deletion event
  Given a directory "src/legacy" was deleted last week
  When the user lists deletions from that timeframe
  Then the tool shows all deleted files from that directory
  And displays total size of deleted content
  And allows batch recovery of all files
```

## Non-Functional Requirements

### Performance
- **Response Time**: Content retrieval < 100ms for files under 1MB
- **Memory Usage**: Stream large files to avoid OOM
- **Caching**: Cache frequently accessed content IDs

### Reliability
- **Corruption Handling**: Graceful degradation when content.dat is corrupted
- **Version Compatibility**: Support multiple IntelliJ versions (2023.x - 2025.x)
- **Data Integrity**: Verify content using checksums when available

### Usability
- **Clear Error Messages**: Explain when content is unavailable
- **Progress Indicators**: Show progress for batch operations
- **File Preview**: Syntax highlighting for recognized file types

## Architecture Design

### Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Interface                         │
│  (search, recover, analyze-deletions commands)          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Content Service Layer                       │
│  - ContentResolver                                       │
│  - DeletionAnalyzer                                     │
│  - RecoveryManager                                      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│           Storage Abstraction Layer                      │
│  - PersistentFSReader (new)                             │
│  - LocalHistoryReader (existing)                        │
│  - ContentCache                                         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Raw Storage Access                          │
│  - content.dat parser                                   │
│  - Page-based reader                                    │
│  - Record decoder                                       │
└──────────────────────────────────────────────────────────┘
```

### Key Classes to Implement

1. **PersistentFSReader**
   ```kotlin
   class PersistentFSReader(val contentDataPath: Path) {
       fun readContent(contentId: Int): ByteArray?
       fun isContentAvailable(contentId: Int): Boolean
       fun getContentMetadata(contentId: Int): ContentMetadata?
   }
   ```

2. **ContentResolver**
   ```kotlin
   class ContentResolver(
       val localHistoryReader: LocalHistoryReader,
       val persistentFSReader: PersistentFSReader
   ) {
       fun resolveContent(changeInfo: ChangeInfo): ResolvedContent?
       fun findDeletedFiles(timeRange: TimeRange): List<DeletedFile>
   }
   ```

3. **RecoveryManager**
   ```kotlin
   class RecoveryManager {
       fun recoverFile(deletedFile: DeletedFile, targetPath: Path)
       fun recoverBatch(deletedFiles: List<DeletedFile>, targetDir: Path)
       fun previewContent(deletedFile: DeletedFile): String
   }
   ```

### Storage Format Parsing

Based on research, the content.dat structure follows AbstractStorage pattern:

1. **Header Structure** (first 32 bytes):
   - Magic number (4 bytes)
   - Version (4 bytes)
   - Record count/metadata (24 bytes)

2. **Record Structure**:
   - Page-based storage (8KB pages)
   - Each record has: ID, address, size, capacity
   - Content stored at computed page offset

3. **Content Retrieval Algorithm**:
   ```kotlin
   fun readContent(contentId: Int): ByteArray? {
       val recordOffset = getRecordOffset(contentId)
       val pageNumber = recordOffset / PAGE_SIZE
       val pageOffset = recordOffset % PAGE_SIZE
       val page = readPage(pageNumber)
       return extractContent(page, pageOffset)
   }
   ```

## Known Issues and Mitigation

### 🐛 Concurrency Risk: Content.dat File Locking [SEVERITY: Medium]

**Description**: IntelliJ may have exclusive locks on content.dat while running.

**Mitigation**:
- Open file in read-only mode
- Implement retry logic with exponential backoff
- Provide option to copy cache files for offline analysis
- Warn users to close IntelliJ for best results

### 🐛 Data Integrity Risk: Corrupted Storage Files [SEVERITY: High]

**Description**: Content.dat may be corrupted or partially written.

**Mitigation**:
- Validate magic numbers and version headers
- Implement checksums for content verification
- Skip corrupted records and continue parsing
- Provide diagnostic mode to report corruption

### 🐛 Performance Risk: Large Content.dat Files [SEVERITY: Medium]

**Description**: Content.dat can grow to multiple GB in size.

**Mitigation**:
- Use memory-mapped files for efficient access
- Implement lazy loading and pagination
- Build index of content IDs on first scan
- Cache frequently accessed content

### 🐛 Compatibility Risk: Format Changes Across Versions [SEVERITY: Medium]

**Description**: Storage format may change between IntelliJ versions.

**Mitigation**:
- Detect version from header and use appropriate parser
- Support multiple format versions
- Graceful fallback for unknown versions
- Document tested version compatibility

## Implementation Roadmap

### Phase 1: Storage Format Research & Prototyping (MVP)
- [x] Analyze IntelliJ source code for storage format
- [ ] Create minimal content.dat parser
- [ ] Successfully extract one piece of content by ID
- [ ] Validate content against known file

### Phase 2: Core Content Extraction
- [ ] Implement PersistentFSReader class
- [ ] Parse content.dat header and record table
- [ ] Extract content by ID with error handling
- [ ] Add encoding detection for text files

### Phase 3: Integration with LocalHistory
- [ ] Connect ContentChange records to PersistentFS
- [ ] Implement ContentResolver service
- [ ] Add content preview to search results
- [ ] Handle missing/unavailable content gracefully

### Phase 4: Recovery Features
- [ ] Implement single file recovery
- [ ] Add batch recovery for multiple files
- [ ] Create directory structure preservation
- [ ] Add progress reporting for large operations

### Phase 5: Deletion Analysis
- [ ] Build deletion timeline view
- [ ] Calculate deletion statistics (size, count)
- [ ] Identify deletion patterns
- [ ] Generate deletion reports

### Phase 6: Production Hardening
- [ ] Add comprehensive error handling
- [ ] Implement performance optimizations
- [ ] Add extensive logging
- [ ] Create user documentation

## Testing Strategy

### Unit Tests
- Content.dat parser with various formats
- Content extraction with edge cases
- Encoding detection accuracy
- Error handling for corrupted data

### Integration Tests
- End-to-end content recovery
- LocalHistory to PersistentFS integration
- Multi-version compatibility
- Large file handling

### Performance Tests
- Content retrieval speed benchmarks
- Memory usage with large files
- Cache effectiveness metrics

## Success Metrics

1. **Functional Success**:
   - Successfully recover 95% of deleted file content
   - Parse content.dat files up to 10GB
   - Support IntelliJ versions 2023.x - 2025.x

2. **Performance Success**:
   - Content retrieval < 100ms for typical files
   - Memory usage < 500MB for typical operations
   - Can process 1000 content IDs per second

3. **User Success**:
   - Users can recover accidentally deleted files
   - Clear understanding of what was deleted when
   - Batch recovery saves hours of manual work

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Storage format undocumented | High | High | Reverse engineering + empirical testing |
| Content.dat corruption | Medium | High | Robust error handling + recovery mode |
| Version incompatibility | Medium | Medium | Multi-version support + version detection |
| Performance issues with large files | Low | Medium | Streaming + caching + memory mapping |
| File locking conflicts | Low | Low | Read-only mode + copy option |

## Dependencies

### External Libraries
- `java.nio.MappedByteBuffer` - Efficient large file access
- `com.github.ajalt.clikt` - CLI framework (existing)
- `org.jetbrains.kotlin.io` - Kotlin I/O extensions

### System Requirements
- Read access to IntelliJ cache directory
- Sufficient memory for content caching (512MB recommended)
- Disk space for recovered files

## Documentation Requirements

1. **User Guide**:
   - How to recover deleted files
   - Understanding deletion analysis
   - Troubleshooting common issues

2. **Technical Documentation**:
   - Content.dat format specification
   - Parser implementation details
   - Performance tuning guide

3. **API Documentation**:
   - Public API for content extraction
   - Integration examples
   - Extension points

## Alternative Approaches Considered

1. **Direct IntelliJ Plugin**: Rejected due to complexity and version coupling
2. **File System Monitoring**: Rejected as doesn't help with past deletions
3. **Git Integration Only**: Rejected as misses uncommitted changes
4. **Binary Diff Approach**: Rejected as requires original files

## Conclusion

This feature will transform the IntelliJ LocalHistory tool from a metadata viewer into a powerful file recovery system. By implementing PersistentFS content extraction, users will be able to:

1. Recover accidentally deleted files with full content
2. Understand the scope and impact of deletion events
3. Audit what code was lost and when
4. Batch recover entire deleted directories

The implementation follows established patterns from IntelliJ's source code while maintaining independence from the IDE itself, ensuring compatibility and reliability.

## References

- IntelliJ Community Source: `platform/platform-impl/src/com/intellij/openapi/vfs/newvfs/persistent/`
- AbstractStorage Pattern: `platform/util/src/com/intellij/util/io/storage/AbstractStorage.java`
- LocalHistory Implementation: `platform/lvcs-impl/src/com/intellij/history/core/`
