package com.stapler.localhistory

import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.core.subcommands
import com.github.ajalt.clikt.parameters.arguments.argument
import com.github.ajalt.clikt.parameters.arguments.default
import com.github.ajalt.clikt.parameters.arguments.optional
import com.github.ajalt.clikt.parameters.options.default
import com.github.ajalt.clikt.parameters.options.flag
import com.github.ajalt.clikt.parameters.options.option
import com.github.ajalt.clikt.parameters.types.choice
import com.github.ajalt.clikt.parameters.types.float
import com.github.ajalt.clikt.parameters.types.int
import com.github.ajalt.clikt.parameters.types.path
import com.stapler.localhistory.analyzer.ContentClassifier
import com.stapler.localhistory.analyzer.ContentType
import com.stapler.localhistory.analyzer.FacadeOrphanDetector
import com.stapler.localhistory.analyzer.OrphanDetector
import com.stapler.localhistory.analyzer.OrphanStatus
import com.stapler.localhistory.analyzer.SimilarityAnalyzer
import com.stapler.localhistory.analyzer.SimilarityConfig
import com.stapler.localhistory.cache.ContentIndexCache
import com.stapler.localhistory.export.ExportFormat
import com.stapler.localhistory.export.ExportOptions
import com.stapler.localhistory.export.LLMExporter
import com.stapler.localhistory.facade.ChangeFilter
import com.stapler.localhistory.facade.ChangeType
import com.stapler.localhistory.facade.LocalHistoryFacadeFactory
import com.stapler.localhistory.model.IndexRecord
import com.stapler.localhistory.parser.CHANGE_TYPES
import com.stapler.localhistory.parser.ChangeInfo
import com.stapler.localhistory.parser.ChangeSetInfo
import com.stapler.localhistory.parser.StorageConstants
import com.stapler.localhistory.parser.VarIntReader
import com.stapler.localhistory.parser.formatSize
import com.stapler.localhistory.parser.getDefaultLocalHistoryDir
import com.stapler.localhistory.parser.parseChangeSet
import com.stapler.localhistory.parser.parseDataFile
import com.stapler.localhistory.parser.parseIndexFile
import com.stapler.localhistory.scanner.ContentScanner
import com.stapler.localhistory.scanner.ScanConfig
import java.nio.file.Path
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.io.path.exists
import kotlin.io.path.readBytes
import kotlin.math.roundToInt

/**
 * IntelliJ LocalHistory Parser
 *
 * Parses IntelliJ's LocalHistory storage to extract file change information.
 * Based on reverse engineering the IntelliJ Community Edition source code.
 *
 * NOTE: Core parsing logic has been moved to com.stapler.localhistory.parser package.
 * This file contains CLI commands and delegates to the parser package.
 */

// Type aliases for backward compatibility - types now live in parser/model packages
typealias Record = IndexRecord

// NOTE: parseChangeSet, parseIndexFile, parseDataFile, getDefaultLocalHistoryDir
// are now imported from com.stapler.localhistory.parser package

// LocalHistoryTool is the main CLI entry point
class LocalHistoryTool : CliktCommand(name = "intellij-localhistory") {
    override fun run() = Unit
}

class SearchCommand : CliktCommand(name = "search", help = "Search for files in LocalHistory") {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val searchTerm by argument(help = "Search term (file name or path fragment)")

    override fun run() {
        val indexPath = localHistoryDir.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryDir.resolve("changes.storageData")

        if (!indexPath.exists() || !dataPath.exists()) {
            echo("Error: LocalHistory files not found in $localHistoryDir")
            return
        }

        echo("Parsing LocalHistory from: $localHistoryDir")
        echo("Searching for: $searchTerm")
        echo()

        val (header, records) = parseIndexFile(indexPath)
        echo("Total records: ${records.size}")

        val changeSets = parseDataFile(dataPath, records)

        val matches = mutableListOf<Triple<Record, ChangeSetInfo, ChangeInfo>>()
        for (record in records) {
            val changeSet = changeSets[record.id] ?: continue
            for (change in changeSet.changes) {
                if (change.path?.contains(searchTerm, ignoreCase = true) == true) {
                    matches.add(Triple(record, changeSet, change))
                }
            }
        }

        if (matches.isNotEmpty()) {
            echo("Found ${matches.size} matches:")
            echo("-".repeat(80))
            for ((record, changeSet, change) in matches.sortedByDescending { it.first.timestamp }) {
                echo("Record #${record.id} @ ${changeSet.timestampStr}")
                echo("  Name: ${changeSet.name ?: "N/A"}")
                echo("  Type: ${change.changeType}")
                echo("  Path: ${change.path}")
                change.contentId?.let { echo("  Content ID: $it") }
                echo()
            }
        } else {
            echo("No matches found in parsed records.")
            echo()
            echo("Trying raw string search in data file...")

            // Fallback to raw string search
            val rawData = dataPath.readBytes()
            val rawString = String(rawData, Charsets.ISO_8859_1)
            val rawMatches = Regex("([^\\x00-\\x1F]{0,200}$searchTerm[^\\x00-\\x1F]{0,50})", RegexOption.IGNORE_CASE)
                .findAll(rawString)
                .map { it.value.trim() }
                .filter { it.length > searchTerm.length + 5 }
                .distinct()
                .take(20)
                .toList()

            if (rawMatches.isNotEmpty()) {
                echo("Found ${rawMatches.size} raw matches:")
                rawMatches.forEach { echo("  $it") }
            } else {
                echo("No matches found.")
            }
        }
    }
}

class ListCommand : CliktCommand(name = "list", help = "List recent changes") {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val limit by option("-n", "--limit", help = "Number of records to show")
        .int()
        .default(20)

    override fun run() {
        val indexPath = localHistoryDir.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryDir.resolve("changes.storageData")

        if (!indexPath.exists() || !dataPath.exists()) {
            echo("Error: LocalHistory files not found in $localHistoryDir")
            return
        }

        val (header, records) = parseIndexFile(indexPath)
        val changeSets = parseDataFile(dataPath, records)

        val sortedRecords = records.sortedByDescending { it.timestamp }

        echo("Recent changes (showing ${minOf(limit, sortedRecords.size)} of ${sortedRecords.size}):")
        echo("-".repeat(80))

        var shown = 0
        for (record in sortedRecords) {
            if (shown >= limit) break
            val changeSet = changeSets[record.id] ?: continue
            if (changeSet.changes.isEmpty()) continue

            echo("Record #${record.id} @ ${changeSet.timestampStr}")
            changeSet.name?.let { echo("  Name: $it") }
            for (change in changeSet.changes) {
                echo("  [${change.changeType}] ${change.path ?: "N/A"}")
            }
            echo()
            shown++
        }
    }
}

class InfoCommand : CliktCommand(name = "info", help = "Show LocalHistory info") {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    override fun run() {
        val indexPath = localHistoryDir.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryDir.resolve("changes.storageData")

        echo("LocalHistory directory: $localHistoryDir")
        echo("Index file: $indexPath (exists: ${indexPath.exists()})")
        echo("Data file: $dataPath (exists: ${dataPath.exists()})")

        if (indexPath.exists() && dataPath.exists()) {
            val (header, records) = parseIndexFile(indexPath)
            echo()
            echo("Header:")
            header.forEach { (k, v) -> echo("  $k: $v") }
            echo()
            echo("Active records: ${records.size}")
            echo("Data file size: ${dataPath.toFile().length()} bytes")
        }

        // Also show content storage info
        echo()
        echo("Content Storage:")
        val cachesDir = getDefaultCachesDir()
        echo("  Caches directory: $cachesDir")
        val format = ContentStorageReader.detectFormat(cachesDir)
        echo("  Storage format: ${format ?: "Not found"}")
        if (format != null) {
            try {
                ContentStorageReader.open(cachesDir).use { reader ->
                    echo("  Record count: ${reader.getRecordCount()}")
                }
            } catch (e: Exception) {
                echo("  Error: ${e.message}")
            }
        }
    }
}

class ContentInfoCommand : CliktCommand(name = "content-info", help = "Show PersistentFS content storage info") {
    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    override fun run() {
        echo("Caches directory: $cachesDir")

        val format = ContentStorageReader.detectFormat(cachesDir)
        if (format == null) {
            echo("Error: No valid content storage found")
            return
        }

        echo("Storage format: $format")

        try {
            ContentStorageReader.open(cachesDir).use { reader ->
                val ids = reader.listContentIds()
                echo("Total content records: ${ids.size}")
                echo()

                // Show first few records as samples
                echo("Sample records:")
                for (id in ids.take(5)) {
                    val record = reader.readContent(id)
                    if (record != null) {
                        echo("  Content ID: $id")
                        echo("    Hash: ${record.cryptoHashHex}")
                        echo("    Size: ${record.content.size} bytes")
                        echo("    Compressed: ${record.isCompressed}")
                        echo("    Text content: ${record.isTextContent()}")
                        if (record.isTextContent() && record.content.size < 200) {
                            echo("    Preview: ${record.contentAsString().take(100)}...")
                        }
                    }
                }
            }
        } catch (e: Exception) {
            echo("Error reading content storage: ${e.message}")
            e.printStackTrace()
        }
    }
}

class ReadContentCommand : CliktCommand(name = "read-content", help = "Read content by ID from PersistentFS") {
    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val contentId by argument(help = "Content ID to read").int()

    private val outputFile by option("-o", "--output", help = "Output file path")
        .path()

    override fun run() {
        try {
            ContentStorageReader.open(cachesDir).use { reader ->
                val record = reader.readContent(contentId)
                if (record == null) {
                    echo("Error: Content ID $contentId not found")
                    return
                }

                echo("Content ID: ${record.contentId}")
                echo("Hash: ${record.cryptoHashHex}")
                echo("Size: ${record.content.size} bytes (uncompressed: ${record.uncompressedSize})")
                echo("Compressed: ${record.isCompressed}")
                echo("Text content: ${record.isTextContent()}")

                if (outputFile != null) {
                    outputFile!!.toFile().writeBytes(record.content)
                    echo("Written to: $outputFile")
                } else {
                    echo()
                    if (record.isTextContent()) {
                        echo("Content:")
                        echo("-".repeat(80))
                        echo(record.contentAsString())
                    } else {
                        echo("Binary content (${record.content.size} bytes)")
                        echo("Use -o/--output to save to file")
                    }
                }
            }
        } catch (e: Exception) {
            echo("Error: ${e.message}")
        }
    }
}

class RecoverCommand : CliktCommand(name = "recover", help = "Recover deleted file content from LocalHistory") {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val searchTerm by argument(help = "File name or path to search for")

    private val outputDir by option("-o", "--output", help = "Output directory for recovered files")
        .path()

    override fun run() {
        val indexPath = localHistoryDir.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryDir.resolve("changes.storageData")

        if (!indexPath.exists() || !dataPath.exists()) {
            echo("Error: LocalHistory files not found in $localHistoryDir")
            return
        }

        echo("Searching for: $searchTerm")
        echo()

        val (_, records) = parseIndexFile(indexPath)
        val changeSets = parseDataFile(dataPath, records)

        // Find all content changes matching the search term
        val matches = mutableListOf<Triple<Record, ChangeSetInfo, ChangeInfo>>()
        for (record in records) {
            val changeSet = changeSets[record.id] ?: continue
            for (change in changeSet.changes) {
                if (change.path?.contains(searchTerm, ignoreCase = true) == true && change.contentId != null) {
                    matches.add(Triple(record, changeSet, change))
                }
            }
        }

        if (matches.isEmpty()) {
            echo("No content changes found matching '$searchTerm'")
            return
        }

        echo("Found ${matches.size} content changes:")
        echo("-".repeat(80))

        // Open content storage
        try {
            ContentStorageReader.open(cachesDir).use { contentReader ->
                for ((index, match) in matches.sortedByDescending { it.first.timestamp }.withIndex()) {
                    val (record, changeSet, change) = match
                    echo("${index + 1}. ${change.path}")
                    echo("   Time: ${changeSet.timestampStr}")
                    echo("   Type: ${change.changeType}")
                    echo("   Content ID: ${change.contentId}")

                    val contentRecord = contentReader.readContent(change.contentId!!)
                    if (contentRecord != null) {
                        echo("   Size: ${contentRecord.content.size} bytes")
                        echo("   Text: ${contentRecord.isTextContent()}")

                        if (outputDir != null) {
                            val fileName = change.path!!.substringAfterLast("/")
                            val outputPath = outputDir!!.resolve("${index + 1}_${changeSet.timestampStr.replace(":", "-")}_$fileName")
                            outputPath.parent?.toFile()?.mkdirs()
                            outputPath.toFile().writeBytes(contentRecord.content)
                            echo("   Saved to: $outputPath")
                        }
                    } else {
                        echo("   Content: NOT AVAILABLE (ID ${change.contentId} not found in storage)")
                    }
                    echo()
                }
            }
        } catch (e: Exception) {
            echo("Error accessing content storage: ${e.message}")
            echo("Content IDs found in LocalHistory, but content storage is not accessible.")
        }
    }
}

class AnalyzeDeletionsCommand : CliktCommand(name = "analyze-deletions", help = "Analyze deletion patterns in LocalHistory") {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val days by option("-n", "--days", help = "Number of days to analyze")
        .int()
        .default(30)

    override fun run() {
        val indexPath = localHistoryDir.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryDir.resolve("changes.storageData")

        if (!indexPath.exists() || !dataPath.exists()) {
            echo("Error: LocalHistory files not found in $localHistoryDir")
            return
        }

        val (_, records) = parseIndexFile(indexPath)
        val changeSets = parseDataFile(dataPath, records)

        val cutoffTime = System.currentTimeMillis() - (days * 24 * 60 * 60 * 1000L)

        // Analyze deletions
        data class DeletionEvent(
            val timestamp: Long,
            val timestampStr: String,
            val path: String,
            val contentId: Int?
        )

        val deletions = mutableListOf<DeletionEvent>()

        for (record in records) {
            if (record.timestamp < cutoffTime) continue
            val changeSet = changeSets[record.id] ?: continue
            for (change in changeSet.changes) {
                if (change.changeType == "Delete" && change.path != null) {
                    deletions.add(DeletionEvent(
                        changeSet.timestamp,
                        changeSet.timestampStr,
                        change.path,
                        change.contentId
                    ))
                }
            }
        }

        echo("Deletion Analysis (last $days days)")
        echo("=".repeat(80))
        echo()

        if (deletions.isEmpty()) {
            echo("No deletions found in the specified time range.")
            return
        }

        echo("Total deletions: ${deletions.size}")
        echo()

        // Group by date
        val byDate = deletions.groupBy { it.timestampStr.substringBefore("T") }
        echo("Deletions by date:")
        for ((date, events) in byDate.toSortedMap(reverseOrder())) {
            echo("  $date: ${events.size} files")
        }
        echo()

        // Group by directory
        val byDir = deletions.groupBy { it.path.substringBeforeLast("/", "<root>") }
        echo("Top directories affected:")
        for ((dir, events) in byDir.entries.sortedByDescending { it.value.size }.take(10)) {
            echo("  ${events.size} files: $dir")
        }
        echo()

        // Large deletion events (same timestamp)
        val byTimestamp = deletions.groupBy { it.timestamp }
        val largeEvents = byTimestamp.filter { it.value.size >= 5 }
        if (largeEvents.isNotEmpty()) {
            echo("Large deletion events (5+ files at once):")
            for ((_, events) in largeEvents.entries.sortedByDescending { it.value.size }) {
                echo("  ${events.first().timestampStr}: ${events.size} files")
                for (event in events.take(5)) {
                    echo("    - ${event.path}")
                }
                if (events.size > 5) {
                    echo("    ... and ${events.size - 5} more")
                }
                echo()
            }
        }

        // Recent deletions
        echo("Recent deletions (last 10):")
        for (event in deletions.sortedByDescending { it.timestamp }.take(10)) {
            echo("  ${event.timestampStr}: ${event.path}")
        }
    }
}

class OrphanAnalyzeCommand : CliktCommand(name = "orphan-analyze", help = "Analyze content for orphaned items") {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val minConfidence by option("-m", "--min-confidence", help = "Minimum confidence for uncertain orphans")
        .float()
        .default(0.7f)

    private val detailed by option("--detailed", help = "Show detailed analysis")
        .flag()

    override fun run() {
        echo("Analyzing orphaned content...")
        echo()

        val detector = OrphanDetector(localHistoryDir, cachesDir)

        // Get all content IDs from storage
        val contentIds = try {
            ContentStorageReader.open(cachesDir).use { reader ->
                echo("Found ${reader.getRecordCount()} content records in storage")
                reader.listContentIds()
            }
        } catch (e: Exception) {
            echo("Error reading content storage: ${e.message}")
            return
        }

        if (detailed) {
            // Show detailed report
            val report = detector.analyzeOrphanPatterns(contentIds)
            report.printSummary()

            echo()
            echo("Finding orphaned content with confidence >= ${minConfidence * 100}%...")
            val orphans = detector.findOrphanedContent(contentIds, minConfidence)

            if (orphans.isNotEmpty()) {
                echo()
                echo("Orphan candidates (${orphans.size} found):")
                echo("-".repeat(80))

                for ((contentId, status) in orphans.take(20)) {
                    echo("Content ID: $contentId")
                    echo("  Status: $status")

                    // Get more details
                    val details = detector.getOrphanDetails(contentId)
                    details.lastReferencePath?.let { echo("  Last path: $it") }
                    details.lastReferenceTime?.let { echo("  Last seen: $it") }
                    details.contentSize?.let { echo("  Size: $it bytes") }
                    echo()
                }

                if (orphans.size > 20) {
                    echo("... and ${orphans.size - 20} more orphan candidates")
                }
            } else {
                echo("No orphan candidates found with confidence >= ${minConfidence * 100}%")
            }
        } else {
            // Quick summary
            val report = detector.analyzeOrphanPatterns(contentIds)
            report.printSummary()
        }
    }
}

class OrphanCheckCommand : CliktCommand(name = "orphan-check", help = "Check if specific content ID is orphaned") {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val contentId by argument(help = "Content ID to check")
        .int()

    override fun run() {
        val detector = OrphanDetector(localHistoryDir, cachesDir)

        echo("Checking orphan status for content ID: $contentId")
        echo()

        val details = detector.getOrphanDetails(contentId)
        details.printDetails()
    }
}

class ScanOrphansCommand : CliktCommand(
    name = "scan-orphans",
    help = "Find orphaned content that may represent deleted files"
) {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val minConfidence by option("--confidence", help = "Minimum orphan confidence (0.0-1.0)")
        .float()
        .default(0.7f)

    private val textOnly by option("--text-only", help = "Only show text content")
        .flag()

    private val limit by option("-n", "--limit", help = "Maximum results to show")
        .int()
        .default(100)

    private val showStats by option("--stats", help = "Show statistics summary")
        .flag(default = true)

    private val format by option("-f", "--format", help = "Output format")
        .choice("human", "markdown", "json")
        .default("human")

    override fun run() {
        // 1. Create OrphanDetector with localHistoryDir and cachesDir
        val detector = OrphanDetector(localHistoryDir, cachesDir)

        // 2. Build reference map from LocalHistory
        echo("Building reference map from LocalHistory...")
        val referenceMap = detector.buildReferenceMap()
        echo("Found ${referenceMap.size} content items with references")
        echo()

        // 3. Open content storage and get all content IDs
        val contentIds = try {
            ContentStorageReader.open(cachesDir).use { reader ->
                echo("Scanning ${reader.getRecordCount()} content records in storage...")
                reader.listContentIds()
            }
        } catch (e: Exception) {
            echo("Error reading content storage: ${e.message}")
            return
        }

        // 4. Check orphan status for each, filtering by confidence
        echo("Analyzing orphan status with minimum confidence ${(minConfidence * 100).roundToInt()}%...")
        val orphanCandidates = mutableListOf<Pair<Int, OrphanStatus>>()
        val classifier = ContentClassifier()

        for (contentId in contentIds) {
            val status = detector.checkOrphanStatus(contentId, referenceMap)

            // Filter by confidence
            when (status) {
                is OrphanStatus.Orphaned -> {
                    orphanCandidates.add(contentId to status)
                }
                is OrphanStatus.Uncertain -> {
                    if (status.confidence >= minConfidence) {
                        orphanCandidates.add(contentId to status)
                    }
                }
                is OrphanStatus.Active -> {
                    // Skip active content
                }
            }
        }

        // 5. Use ContentClassifier to filter by text if needed
        val filteredOrphans = if (textOnly) {
            echo("Filtering for text content only...")
            val textOrphans = mutableListOf<Pair<Int, OrphanStatus>>()

            ContentStorageReader.open(cachesDir).use { reader ->
                for ((contentId, status) in orphanCandidates) {
                    try {
                        val record = reader.readContent(contentId)
                        if (record != null && classifier.isTextContent(record.content)) {
                            textOrphans.add(contentId to status)
                        }
                    } catch (e: Exception) {
                        // Skip content that can't be read
                    }
                }
            }
            textOrphans
        } else {
            orphanCandidates
        }

        // Sort by confidence (orphaned first, then by confidence level)
        val sortedOrphans = filteredOrphans.sortedWith(compareBy(
            { it.second !is OrphanStatus.Orphaned },
            {
                when (val s = it.second) {
                    is OrphanStatus.Uncertain -> -s.confidence
                    else -> 0f
                }
            }
        ))

        // 6. Show stats: total orphans, by confidence level, by type, total size
        if (showStats) {
            showStatistics(contentIds, sortedOrphans, classifier)
        }

        // 7. Output orphaned content list with previews
        when (format) {
            "human" -> outputHumanFormat(sortedOrphans.take(limit), detector, classifier)
            "markdown" -> outputMarkdownFormat(sortedOrphans.take(limit), detector, classifier)
            "json" -> outputJsonFormat(sortedOrphans.take(limit), detector)
        }

        if (sortedOrphans.size > limit) {
            echo()
            echo("Showing ${limit} of ${sortedOrphans.size} orphaned content items.")
            echo("Use --limit to show more results.")
        }
    }

    private fun showStatistics(
        allContentIds: List<Int>,
        orphans: List<Pair<Int, OrphanStatus>>,
        classifier: ContentClassifier
    ) {
        echo()
        echo("=== Orphan Scan Statistics ===")
        echo("Total content records scanned: ${allContentIds.size}")
        echo("Orphaned content found: ${orphans.size}")

        // Break down by confidence level
        val highConfidence = orphans.count {
            it.second is OrphanStatus.Orphaned ||
            (it.second is OrphanStatus.Uncertain && (it.second as OrphanStatus.Uncertain).confidence > 0.9f)
        }
        val mediumConfidence = orphans.count {
            it.second is OrphanStatus.Uncertain &&
            (it.second as OrphanStatus.Uncertain).confidence in 0.7f..0.9f
        }
        val lowConfidence = orphans.count {
            it.second is OrphanStatus.Uncertain &&
            (it.second as OrphanStatus.Uncertain).confidence < 0.7f
        }

        echo()
        echo("By confidence level:")
        echo("  High (>90%): $highConfidence")
        echo("  Medium (70-90%): $mediumConfidence")
        echo("  Low (<70%): $lowConfidence")

        // Analyze content types and sizes
        var totalSize = 0L
        var textCount = 0
        var binaryCount = 0
        val fileTypes = mutableMapOf<String, Int>()

        ContentStorageReader.open(cachesDir).use { reader ->
            for ((contentId, _) in orphans.take(1000)) { // Sample first 1000 for performance
                try {
                    val record = reader.readContent(contentId)
                    if (record != null) {
                        totalSize += record.content.size

                        if (classifier.isTextContent(record.content)) {
                            textCount++
                            val fileType = classifier.detectFileType(record.content)
                            if (fileType != null) {
                                fileTypes[fileType.extension] =
                                    fileTypes.getOrDefault(fileType.extension, 0) + 1
                            }
                        } else {
                            binaryCount++
                        }
                    }
                } catch (e: Exception) {
                    // Skip content that can't be read
                }
            }
        }

        echo()
        echo("By content type:")
        echo("  Text: $textCount")
        echo("  Binary: $binaryCount")

        if (fileTypes.isNotEmpty()) {
            echo()
            echo("Top 5 file types found:")
            fileTypes.entries
                .sortedByDescending { it.value }
                .take(5)
                .forEach { (type, count) ->
                    echo("  .$type: $count")
                }
        }

        echo()
        echo("Total size of orphaned content: ${formatSize(totalSize)}")
        if (orphans.size > 1000) {
            echo("(Size calculated from first 1000 items)")
        }
        echo()
    }

    private fun outputHumanFormat(
        orphans: List<Pair<Int, OrphanStatus>>,
        detector: OrphanDetector,
        classifier: ContentClassifier
    ) {
        if (orphans.isEmpty()) {
            echo("No orphaned content found with confidence >= ${(minConfidence * 100).roundToInt()}%")
            return
        }

        echo("-".repeat(80))
        echo("Orphaned Content (${orphans.size} items)")
        echo("-".repeat(80))

        ContentStorageReader.open(cachesDir).use { reader ->
            for ((contentId, status) in orphans) {
                echo()
                echo("Content ID: $contentId")
                echo("  Status: $status")

                val details = detector.getOrphanDetails(contentId)
                details.lastReferencePath?.let {
                    echo("  Last path: $it")
                }
                details.lastReferenceTime?.let {
                    val timeStr = it.atZone(ZoneId.systemDefault())
                        .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
                    echo("  Last seen: $timeStr")
                }

                try {
                    val record = reader.readContent(contentId)
                    if (record != null) {
                        echo("  Size: ${formatSize(record.content.size.toLong())}")
                        echo("  Hash: ${record.cryptoHashHex}")

                        val analysis = classifier.analyzeContent(record.content)
                        echo("  Type: ${analysis.description}")

                        if (analysis.isText && analysis.preview != null) {
                            echo("  Preview:")
                            analysis.preview.lines().take(3).forEach { line ->
                                echo("    ${line.take(100)}")
                            }
                        }
                    }
                } catch (e: Exception) {
                    echo("  Error reading content: ${e.message}")
                }
            }
        }
    }

    private fun outputMarkdownFormat(
        orphans: List<Pair<Int, OrphanStatus>>,
        detector: OrphanDetector,
        classifier: ContentClassifier
    ) {
        echo("# Orphaned Content Scan Results")
        echo()
        echo("**Minimum Confidence:** ${(minConfidence * 100).roundToInt()}%")
        echo("**Total Orphans Found:** ${orphans.size}")
        echo()

        if (orphans.isEmpty()) {
            echo("No orphaned content found.")
            return
        }

        echo("## Orphaned Content Items")
        echo()
        echo("| Content ID | Status | Last Path | Size | Type |")
        echo("|------------|--------|-----------|------|------|")

        ContentStorageReader.open(cachesDir).use { reader ->
            for ((contentId, status) in orphans) {
                val details = detector.getOrphanDetails(contentId)
                val statusStr = when (status) {
                    is OrphanStatus.Orphaned -> "Orphaned"
                    is OrphanStatus.Uncertain -> "${(status.confidence * 100).roundToInt()}%"
                    else -> status.toString()
                }

                val lastPath = details.lastReferencePath?.let {
                    "`${it.substringAfterLast("/")}`"
                } ?: "-"

                var size = "-"
                var type = "-"

                try {
                    val record = reader.readContent(contentId)
                    if (record != null) {
                        size = formatSize(record.content.size.toLong())
                        val analysis = classifier.analyzeContent(record.content)
                        type = analysis.fileTypeInfo?.extension ?:
                               if (analysis.isText) "text" else "binary"
                    }
                } catch (e: Exception) {
                    // Keep defaults
                }

                echo("| $contentId | $statusStr | $lastPath | $size | $type |")
            }
        }
    }

    private fun outputJsonFormat(
        orphans: List<Pair<Int, OrphanStatus>>,
        detector: OrphanDetector
    ) {
        echo("{")
        echo("  \"minConfidence\": $minConfidence,")
        echo("  \"totalOrphans\": ${orphans.size},")
        echo("  \"orphans\": [")

        orphans.forEachIndexed { index, (contentId, status) ->
            val details = detector.getOrphanDetails(contentId)

            echo("    {")
            echo("      \"contentId\": $contentId,")
            echo("      \"status\": \"$status\",")

            when (status) {
                is OrphanStatus.Uncertain -> {
                    echo("      \"confidence\": ${status.confidence},")
                    echo("      \"reason\": \"${status.reason}\",")
                }
                else -> {}
            }

            details.lastReferencePath?.let {
                echo("      \"lastPath\": \"${it.replace("\"", "\\\"")}\",")
            }
            details.lastReferenceTime?.let {
                echo("      \"lastSeen\": \"$it\",")
            }
            details.contentSize?.let {
                echo("      \"size\": $it,")
            }
            details.contentHash?.let {
                echo("      \"hash\": \"$it\"")
            } ?: echo("      \"hash\": null")

            if (index < orphans.size - 1) {
                echo("    },")
            } else {
                echo("    }")
            }
        }

        echo("  ]")
        echo("}")
    }

    private fun formatSize(bytes: Long): String {
        return when {
            bytes < 1024 -> "$bytes B"
            bytes < 1024 * 1024 -> "${bytes / 1024} KB"
            bytes < 1024 * 1024 * 1024 -> "${bytes / (1024 * 1024)} MB"
            else -> "${bytes / (1024 * 1024 * 1024)} GB"
        }
    }
}

class OrphanCleanCommand : CliktCommand(name = "orphan-clean", help = "List orphaned content that could be cleaned up") {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val minConfidence by option("-m", "--min-confidence", help = "Minimum confidence for cleanup candidates")
        .float()
        .default(0.9f)

    private val estimateSize by option("--estimate-size", help = "Estimate total size of orphaned content")
        .flag()

    override fun run() {
        echo("Finding high-confidence orphaned content...")
        echo()

        val detector = OrphanDetector(localHistoryDir, cachesDir)

        // Get all content IDs
        val contentIds = try {
            ContentStorageReader.open(cachesDir).use { reader ->
                reader.listContentIds()
            }
        } catch (e: Exception) {
            echo("Error reading content storage: ${e.message}")
            return
        }

        val orphans = detector.findOrphanedContent(contentIds, minConfidence)

        if (orphans.isEmpty()) {
            echo("No orphaned content found with confidence >= ${minConfidence * 100}%")
            return
        }

        echo("Found ${orphans.size} orphaned content items with confidence >= ${minConfidence * 100}%")
        echo()

        // Group by status type
        val definiteOrphans = orphans.filter { it.second is OrphanStatus.Orphaned }
        val highConfidenceOrphans = orphans.filter {
            it.second is OrphanStatus.Uncertain && (it.second as OrphanStatus.Uncertain).confidence >= 0.9f
        }

        if (definiteOrphans.isNotEmpty()) {
            echo("Definite orphans (${definiteOrphans.size} items):")
            echo("-".repeat(40))
            for ((contentId, _) in definiteOrphans.take(10)) {
                val details = detector.getOrphanDetails(contentId)
                echo("  ID: $contentId")
                details.lastReferencePath?.let { echo("    Last path: $it") }
                details.contentSize?.let { echo("    Size: $it bytes") }
            }
            if (definiteOrphans.size > 10) {
                echo("  ... and ${definiteOrphans.size - 10} more")
            }
            echo()
        }

        if (highConfidenceOrphans.isNotEmpty()) {
            echo("High confidence orphans (${highConfidenceOrphans.size} items):")
            echo("-".repeat(40))
            for ((contentId, status) in highConfidenceOrphans.take(10)) {
                val details = detector.getOrphanDetails(contentId)
                echo("  ID: $contentId")
                if (status is OrphanStatus.Uncertain) {
                    echo("    Reason: ${status.reason}")
                }
                details.lastReferencePath?.let { echo("    Last path: $it") }
                details.contentSize?.let { echo("    Size: $it bytes") }
            }
            if (highConfidenceOrphans.size > 10) {
                echo("  ... and ${highConfidenceOrphans.size - 10} more")
            }
        }

        if (estimateSize) {
            echo()
            echo("Calculating total size of orphaned content...")

            var totalSize = 0L
            var errorCount = 0

            ContentStorageReader.open(cachesDir).use { reader ->
                for ((contentId, _) in orphans) {
                    try {
                        val record = reader.readContent(contentId)
                        if (record != null) {
                            totalSize += record.content.size
                        }
                    } catch (e: Exception) {
                        errorCount++
                    }
                }
            }

            echo()
            echo("Total orphaned content size: ${formatSize(totalSize)}")
            if (errorCount > 0) {
                echo("($errorCount content items could not be read)")
            }
        }
    }

    private fun formatSize(bytes: Long): String {
        return when {
            bytes < 1024 -> "$bytes bytes"
            bytes < 1024 * 1024 -> "${bytes / 1024} KB"
            bytes < 1024 * 1024 * 1024 -> "${bytes / (1024 * 1024)} MB"
            else -> "${bytes / (1024 * 1024 * 1024)} GB"
        }
    }
}

class FindDeletedCommand : CliktCommand(
    name = "find-deleted",
    help = "Discover potentially deleted content by searching content patterns"
) {
    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val pattern by option("-p", "--pattern", help = "Text pattern to search for (regex)")

    private val contentType by option("-t", "--type", help = "Filter by content type")
        .choice("text", "binary", "all")
        .default("all")

    private val minSize by option("--min-size", help = "Minimum content size in bytes")
        .int()

    private val maxSize by option("--max-size", help = "Maximum content size in bytes")
        .int()

    private val limit by option("-n", "--limit", help = "Maximum number of results")
        .int()
        .default(50)

    private val showPreview by option("--preview", help = "Show content preview")
        .flag(default = true)

    private val format by option("-f", "--format", help = "Output format")
        .choice("human", "markdown", "json")
        .default("human")

    override fun run() {
        // Open content storage
        val storageFormat = ContentStorageReader.detectFormat(cachesDir)
        if (storageFormat == null) {
            echo("Error: No valid content storage found in $cachesDir")
            return
        }

        echo("Scanning content storage (format: $storageFormat)...")
        echo()

        try {
            ContentStorageReader.open(cachesDir).use { reader ->
                // Create scanner with configuration
                val scanConfig = ScanConfig(
                    maxRecords = limit,
                    textOnly = contentType == "text",
                    minSize = minSize ?: 0,
                    maxSize = maxSize ?: Int.MAX_VALUE,
                    skipCorrupted = true
                )

                val scanner = ContentScanner(reader)
                val classifier = ContentClassifier()

                // Scan content
                val scanResults = if (pattern != null) {
                    val regex = Regex(pattern!!)
                    scanner.scanByPattern(regex, scanConfig)
                } else {
                    scanner.scan(scanConfig)
                }

                // Convert sequence to list and filter by content type if needed
                val results = scanResults.toList()
                val filteredResults = when (contentType) {
                    "binary" -> results.filter { !it.metadata.isText }
                    else -> results
                }

                // Output results
                when (format) {
                    "json" -> outputJson(filteredResults)
                    "markdown" -> outputMarkdown(filteredResults, classifier)
                    else -> outputHuman(filteredResults, classifier)
                }
            }
        } catch (e: Exception) {
            echo("Error scanning content: ${e.message}")
            e.printStackTrace()
        }
    }

    private fun outputHuman(results: List<com.stapler.localhistory.scanner.ContentScanResult>, classifier: ContentClassifier) {
        if (results.isEmpty()) {
            echo("No matching content found.")
            return
        }

        echo("Found ${results.size} matching content items:")
        echo("-".repeat(80))

        for ((index, result) in results.withIndex()) {
            echo("${index + 1}. Content ID: ${result.metadata.contentId}")
            echo("   Hash: ${result.metadata.hash}")
            echo("   Size: ${result.metadata.size} bytes")
            echo("   Type: ${if (result.metadata.isText) "Text" else "Binary"}")
            result.fileType?.let { echo("   File type: $it") }

            if (showPreview && result.preview != null) {
                echo("   Preview:")
                result.preview.lines().take(5).forEach { line ->
                    echo("     ${line.take(100)}")
                }
            }
            echo()
        }
    }

    private fun outputMarkdown(results: List<com.stapler.localhistory.scanner.ContentScanResult>, classifier: ContentClassifier) {
        if (results.isEmpty()) {
            echo("# No Results Found")
            return
        }

        echo("# Content Scan Results")
        echo()
        echo("Found ${results.size} matching content items")
        echo()

        for ((index, result) in results.withIndex()) {
            echo("## ${index + 1}. Content ID ${result.metadata.contentId}")
            echo()
            echo("- **Hash**: `${result.metadata.hash}`")
            echo("- **Size**: ${result.metadata.size} bytes")
            echo("- **Type**: ${if (result.metadata.isText) "Text" else "Binary"}")
            result.fileType?.let { echo("- **File type**: $it") }
            echo()

            if (showPreview && result.preview != null) {
                echo("### Preview")
                echo()
                echo("```")
                result.preview.lines().take(10).forEach { line ->
                    echo(line.take(120))
                }
                echo("```")
                echo()
            }
        }
    }

    private fun outputJson(results: List<com.stapler.localhistory.scanner.ContentScanResult>) {
        // Simple JSON output (could use a JSON library for proper formatting)
        echo("{")
        echo("  \"count\": ${results.size},")
        echo("  \"results\": [")

        for ((index, result) in results.withIndex()) {
            echo("    {")
            echo("      \"contentId\": ${result.metadata.contentId},")
            echo("      \"hash\": \"${result.metadata.hash}\",")
            echo("      \"size\": ${result.metadata.size},")
            echo("      \"isText\": ${result.metadata.isText},")
            echo("      \"isCompressed\": ${result.metadata.isCompressed}")

            if (result.fileType != null) {
                echo(",      \"fileType\": \"${result.fileType}\"")
            }

            if (showPreview && result.preview != null) {
                val escapedPreview = result.preview
                    .replace("\\", "\\\\")
                    .replace("\"", "\\\"")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t")
                    .take(500)
                echo(",      \"preview\": \"$escapedPreview\"")
            }

            echo("    }${if (index < results.size - 1) "," else ""}")
        }

        echo("  ]")
        echo("}")
    }
}

class AnalyzePatternsCommand : CliktCommand(
    name = "analyze-patterns",
    help = "Analyze content patterns including similarity and duplicates"
) {
    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val similarityThreshold by option("-s", "--similarity", help = "Similarity threshold (0.0-1.0)")
        .float()
        .default(0.7f)

    private val showDuplicates by option("--duplicates", help = "Show duplicate content")
        .flag()

    private val showGroups by option("--groups", help = "Show similar content groups")
        .flag(default = true)

    private val limit by option("-n", "--limit", help = "Maximum results to show")
        .int()
        .default(50)

    private val useCache by option("--cache", help = "Use content index cache")
        .flag(default = true)

    private val format by option("-f", "--format", help = "Output format")
        .choice("human", "markdown", "json")
        .default("human")

    override fun run() {
        echo("Analyzing content patterns...")
        echo()

        // Try to use cache first
        val scanResults = if (useCache) {
            loadFromCache() ?: scanFresh()
        } else {
            scanFresh()
        }

        if (scanResults.isEmpty()) {
            echo("No content found to analyze.")
            return
        }

        echo("Analyzing ${scanResults.size} content items for similarity...")
        echo()

        val analyzer = SimilarityAnalyzer()
        val config = SimilarityConfig(
            similarityThreshold = similarityThreshold,
            duplicateThreshold = 0.95f
        )

        val result = analyzer.analyze(scanResults, config)

        when (format) {
            "json" -> outputJson(result)
            "markdown" -> outputMarkdown(result)
            else -> outputHuman(result)
        }
    }

    private fun loadFromCache(): List<com.stapler.localhistory.scanner.ContentScanResult>? {
        return try {
            val cache = ContentIndexCache.forStorage(cachesDir)
            if (cache.load() && cache.isValid()) {
                echo("Using cached content index (${cache.size()} entries)")
                cache.getAllAsScanResults()
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }

    private fun scanFresh(): List<com.stapler.localhistory.scanner.ContentScanResult> {
        return try {
            ContentStorageReader.open(cachesDir).use { reader ->
                val scanner = ContentScanner(reader)
                val config = ScanConfig(
                    maxRecords = 1000,  // Limit for performance
                    textOnly = true,
                    skipCorrupted = true
                )
                scanner.scan(config).toList()
            }
        } catch (e: Exception) {
            echo("Error scanning content: ${e.message}")
            emptyList()
        }
    }

    private fun outputHuman(result: com.stapler.localhistory.analyzer.SimilarityAnalysisResult) {
        echo("=== Pattern Analysis Results ===")
        echo("Total analyzed: ${result.totalAnalyzed}")
        echo("Grouped: ${result.groupedCount}")
        echo("Ungrouped: ${result.ungroupedCount}")
        echo("Duplicate pairs: ${result.duplicateCount}")
        echo("Groups found: ${result.groupCount}")
        echo()

        if (showDuplicates && result.duplicates.isNotEmpty()) {
            echo("Duplicate Content Pairs:")
            echo("-".repeat(40))
            result.duplicates.take(limit).forEach { (id1, id2) ->
                echo("  Content $id1 <-> Content $id2")
            }
            if (result.duplicates.size > limit) {
                echo("  ... and ${result.duplicates.size - limit} more")
            }
            echo()
        }

        if (showGroups && result.groups.isNotEmpty()) {
            echo("Similar Content Groups:")
            echo("-".repeat(40))
            result.groups.take(limit).forEach { group ->
                echo("Group #${group.id} (${group.size} items, avg similarity: ${(group.averageSimilarity * 100).toInt()}%)")
                echo("  Type: ${group.fileType ?: "mixed"}")
                echo("  Total size: ${formatSize(group.totalSize)}")
                echo("  Members: ${group.members.take(5).map { it.metadata.contentId }.joinToString(", ")}")
                if (group.size > 5) {
                    echo("  ... and ${group.size - 5} more")
                }
                echo()
            }
            if (result.groups.size > limit) {
                echo("... and ${result.groups.size - limit} more groups")
            }
        }
    }

    private fun outputMarkdown(result: com.stapler.localhistory.analyzer.SimilarityAnalysisResult) {
        echo("# Pattern Analysis Results")
        echo()
        echo("| Metric | Value |")
        echo("|--------|-------|")
        echo("| Total analyzed | ${result.totalAnalyzed} |")
        echo("| Grouped | ${result.groupedCount} |")
        echo("| Ungrouped | ${result.ungroupedCount} |")
        echo("| Duplicate pairs | ${result.duplicateCount} |")
        echo("| Groups found | ${result.groupCount} |")
        echo()

        if (showDuplicates && result.duplicates.isNotEmpty()) {
            echo("## Duplicate Content Pairs")
            echo()
            echo("| Content ID 1 | Content ID 2 |")
            echo("|--------------|--------------|")
            result.duplicates.take(limit).forEach { (id1, id2) ->
                echo("| $id1 | $id2 |")
            }
            echo()
        }

        if (showGroups && result.groups.isNotEmpty()) {
            echo("## Similar Content Groups")
            echo()
            result.groups.take(limit).forEach { group ->
                echo("### Group #${group.id}")
                echo("- **Size**: ${group.size} items")
                echo("- **Avg Similarity**: ${(group.averageSimilarity * 100).toInt()}%")
                echo("- **Type**: ${group.fileType ?: "mixed"}")
                echo("- **Total Size**: ${formatSize(group.totalSize)}")
                echo()
            }
        }
    }

    private fun outputJson(result: com.stapler.localhistory.analyzer.SimilarityAnalysisResult) {
        echo("{")
        echo("  \"totalAnalyzed\": ${result.totalAnalyzed},")
        echo("  \"groupedCount\": ${result.groupedCount},")
        echo("  \"ungroupedCount\": ${result.ungroupedCount},")
        echo("  \"duplicateCount\": ${result.duplicateCount},")
        echo("  \"groupCount\": ${result.groupCount},")

        echo("  \"duplicates\": [")
        result.duplicates.take(limit).forEachIndexed { index, (id1, id2) ->
            val comma = if (index < result.duplicates.take(limit).size - 1) "," else ""
            echo("    {\"id1\": $id1, \"id2\": $id2}$comma")
        }
        echo("  ],")

        echo("  \"groups\": [")
        result.groups.take(limit).forEachIndexed { index, group ->
            echo("    {")
            echo("      \"id\": ${group.id},")
            echo("      \"size\": ${group.size},")
            echo("      \"avgSimilarity\": ${group.averageSimilarity},")
            echo("      \"fileType\": ${group.fileType?.let { "\"$it\"" } ?: "null"},")
            echo("      \"totalSize\": ${group.totalSize},")
            echo("      \"memberIds\": [${group.members.map { it.metadata.contentId }.joinToString(", ")}]")
            val comma = if (index < result.groups.take(limit).size - 1) "," else ""
            echo("    }$comma")
        }
        echo("  ]")
        echo("}")
    }

    private fun formatSize(bytes: Long): String {
        return when {
            bytes < 1024 -> "$bytes B"
            bytes < 1024 * 1024 -> "${bytes / 1024} KB"
            bytes < 1024 * 1024 * 1024 -> "${bytes / (1024 * 1024)} MB"
            else -> "${bytes / (1024 * 1024 * 1024)} GB"
        }
    }
}

class ExportLLMCommand : CliktCommand(
    name = "export-llm",
    help = "Export content analysis in LLM-friendly formats"
) {
    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val format by option("-f", "--format", help = "Output format")
        .choice("markdown", "json", "csv")
        .default("markdown")

    private val includeContent by option("--content", help = "Include content previews")
        .flag()

    private val includePrompt by option("--prompt", help = "Include analysis prompt")
        .flag(default = true)

    private val groupByType by option("--group", help = "Group results by file type")
        .flag(default = true)

    private val maxContentLength by option("--max-length", help = "Maximum content preview length")
        .int()
        .default(1000)

    private val limit by option("-n", "--limit", help = "Maximum results to include")
        .int()
        .default(100)

    private val outputFile by option("-o", "--output", help = "Output file path")
        .path()

    private val textOnly by option("--text-only", help = "Only include text content")
        .flag()

    override fun run() {
        echo("Preparing LLM export...")
        echo()

        // Scan content
        val scanResults = try {
            ContentStorageReader.open(cachesDir).use { reader ->
                val scanner = ContentScanner(reader)
                val config = ScanConfig(
                    maxRecords = limit,
                    textOnly = textOnly,
                    skipCorrupted = true
                )
                scanner.scan(config).toList()
            }
        } catch (e: Exception) {
            echo("Error scanning content: ${e.message}")
            return
        }

        if (scanResults.isEmpty()) {
            echo("No content found to export.")
            return
        }

        echo("Found ${scanResults.size} content items")

        // Create exporter
        val exporter = LLMExporter()
        val exportFormat = when (format) {
            "json" -> ExportFormat.JSON
            "csv" -> ExportFormat.CSV
            else -> ExportFormat.Markdown
        }

        val options = ExportOptions(
            format = exportFormat,
            includeContent = includeContent,
            maxContentLength = maxContentLength,
            includePrompt = includePrompt,
            groupByType = groupByType
        )

        // Try to get deletion events for pattern analysis
        val deletionEvents = try {
            getDeletionEvents()
        } catch (e: Exception) {
            null
        }

        // Generate export
        val output = if (deletionEvents != null && deletionEvents.isNotEmpty()) {
            echo("Including deletion pattern analysis (${deletionEvents.size} events)")
            exporter.exportWithPatternAnalysis(scanResults, deletionEvents, options)
        } else {
            exporter.export(scanResults, options)
        }

        // Output result
        if (outputFile != null) {
            outputFile!!.toFile().writeText(output)
            echo("Export written to: $outputFile")
        } else {
            echo()
            echo(output)
        }
    }

    private fun getDeletionEvents(): List<com.stapler.localhistory.export.DeletionEvent>? {
        val indexPath = localHistoryDir.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryDir.resolve("changes.storageData")

        if (!indexPath.exists() || !dataPath.exists()) {
            return null
        }

        val (_, records) = parseIndexFile(indexPath)
        val changeSets = parseDataFile(dataPath, records)

        val deletionEvents = mutableListOf<com.stapler.localhistory.export.DeletionEvent>()

        for (record in records) {
            val changeSet = changeSets[record.id] ?: continue
            for (change in changeSet.changes) {
                if (change.changeType == "Delete" && change.path != null) {
                    deletionEvents.add(
                        com.stapler.localhistory.export.DeletionEvent(
                            timestamp = changeSet.timestamp,
                            path = change.path,
                            contentId = change.contentId
                        )
                    )
                }
            }
        }

        return deletionEvents
    }
}

class CacheCommand : CliktCommand(
    name = "cache",
    help = "Manage content index cache for faster operations"
) {
    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val action by argument(help = "Action: build, clear, stats, update")
        .choice("build", "clear", "stats", "update")
        .default("stats")

    override fun run() {
        val cache = ContentIndexCache.forStorage(cachesDir)

        when (action) {
            "build" -> buildCache(cache)
            "clear" -> clearCache(cache)
            "update" -> updateCache(cache)
            "stats" -> showStats(cache)
        }
    }

    private fun buildCache(cache: ContentIndexCache) {
        echo("Building content index cache...")

        try {
            ContentStorageReader.open(cachesDir).use { reader ->
                val classifier = ContentClassifier()
                var lastProgress = 0

                val count = cache.buildFromStorage(reader, classifier) { current, total ->
                    val progress = (current * 100) / total
                    if (progress != lastProgress && progress % 10 == 0) {
                        echo("Progress: $progress%")
                        lastProgress = progress
                    }
                }

                if (cache.save()) {
                    echo("Cache built successfully: $count entries")
                } else {
                    echo("Cache built but failed to save to disk")
                }
            }
        } catch (e: Exception) {
            echo("Error building cache: ${e.message}")
        }
    }

    private fun clearCache(cache: ContentIndexCache) {
        cache.clear()
        echo("Cache cleared")
    }

    private fun updateCache(cache: ContentIndexCache) {
        echo("Updating content index cache...")

        // Load existing cache
        val loaded = cache.load()
        if (loaded) {
            echo("Loaded existing cache with ${cache.size()} entries")
        }

        try {
            ContentStorageReader.open(cachesDir).use { reader ->
                val classifier = ContentClassifier()
                val added = cache.updateIncremental(reader, classifier)

                if (cache.save()) {
                    echo("Cache updated: $added new entries (total: ${cache.size()})")
                } else {
                    echo("Cache updated but failed to save to disk")
                }
            }
        } catch (e: Exception) {
            echo("Error updating cache: ${e.message}")
        }
    }

    private fun showStats(cache: ContentIndexCache) {
        val loaded = cache.load()
        if (!loaded) {
            echo("No cache found or cache is invalid")
            echo("Run 'cache build' to create a new cache")
            return
        }

        cache.getStats().print()
    }
}

class FacadeSearchCommand : CliktCommand(
    name = "facade-search",
    help = "Search LocalHistory using the facade API (improved format support)"
) {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val searchTerm by argument(help = "Search term (file name or path fragment)")

    private val limit by option("-n", "--limit", help = "Maximum results to show")
        .int()
        .default(50)

    private val projectPath by option("-p", "--project", help = "Filter by project path")

    override fun run() {
        echo("Searching LocalHistory using facade API...")
        echo()

        try {
            val facade = LocalHistoryFacadeFactory.create(localHistoryDir, cachesDir)
            echo("Using implementation: ${facade.getImplementationType()}")
            echo()

            facade.use { f ->
                val results = f.searchByPath(searchTerm, limit)

                if (results.isEmpty()) {
                    echo("No matches found for '$searchTerm'")
                    return
                }

                echo("Found ${results.size} matches:")
                echo("-".repeat(80))

                for ((changeSet, change) in results) {
                    // Apply project filter if specified
                    if (projectPath != null && change.path?.contains(projectPath!!) != true) {
                        continue
                    }

                    val timestampStr = java.time.Instant.ofEpochMilli(changeSet.timestamp)
                        .atZone(java.time.ZoneId.systemDefault())
                        .format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE_TIME)

                    echo("$timestampStr")
                    echo("  Type: ${change.type}")
                    echo("  Path: ${change.path}")
                    change.contentId?.let { echo("  Content ID: $it") }
                    changeSet.name?.let { echo("  Activity: $it") }
                    echo()
                }
            }
        } catch (e: Exception) {
            echo("Error: ${e.message}")
        }
    }
}

class FacadeListCommand : CliktCommand(
    name = "facade-list",
    help = "List recent changes using the facade API (improved format support)"
) {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val limit by option("-n", "--limit", help = "Number of change sets to show")
        .int()
        .default(20)

    private val changeType by option("-t", "--type", help = "Filter by change type")
        .choice("create", "delete", "content", "rename", "move", "all")
        .default("all")

    private val projectPath by option("-p", "--project", help = "Filter by project path")

    override fun run() {
        echo("Listing recent changes using facade API...")
        echo()

        try {
            val facade = LocalHistoryFacadeFactory.create(localHistoryDir, cachesDir)
            echo("Using implementation: ${facade.getImplementationType()}")
            echo()

            facade.use { f ->
                val typeFilter = when (changeType) {
                    "create" -> setOf(ChangeType.CREATE_FILE, ChangeType.CREATE_DIRECTORY)
                    "delete" -> setOf(ChangeType.DELETE)
                    "content" -> setOf(ChangeType.CONTENT_CHANGE)
                    "rename" -> setOf(ChangeType.RENAME)
                    "move" -> setOf(ChangeType.MOVE)
                    else -> null
                }

                val filter = ChangeFilter(
                    limit = limit,
                    changeTypes = typeFilter,
                    projectPath = projectPath
                )

                val changeSets = f.getChangeSets(filter)

                if (changeSets.isEmpty()) {
                    echo("No change sets found")
                    return
                }

                echo("Recent changes (showing ${changeSets.size}):")
                echo("-".repeat(80))

                for (cs in changeSets) {
                    val timestampStr = java.time.Instant.ofEpochMilli(cs.timestamp)
                        .atZone(java.time.ZoneId.systemDefault())
                        .format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE_TIME)

                    echo("ChangeSet #${cs.id} @ $timestampStr")
                    cs.name?.let { echo("  Name: $it") }
                    echo("  Changes: ${cs.changes.size}")

                    for (change in cs.changes.take(5)) {
                        echo("    [${change.type}] ${change.path ?: "N/A"}")
                        change.contentId?.let { echo("      Content ID: $it") }
                    }

                    if (cs.changes.size > 5) {
                        echo("    ... and ${cs.changes.size - 5} more changes")
                    }
                    echo()
                }
            }
        } catch (e: Exception) {
            echo("Error: ${e.message}")
        }
    }
}

class FacadeStatsCommand : CliktCommand(
    name = "facade-stats",
    help = "Show LocalHistory statistics using the facade API"
) {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    override fun run() {
        echo("LocalHistory Statistics (via Facade API)")
        echo("=".repeat(50))
        echo()

        try {
            val facade = LocalHistoryFacadeFactory.create(localHistoryDir, cachesDir)

            facade.use { f ->
                echo("Implementation: ${f.getImplementationType()}")
                echo()

                val stats = f.getStats()

                echo("Change History:")
                echo("  Total change sets: ${stats.totalChangeSets}")
                echo("  Total changes: ${stats.totalChanges}")
                echo()

                echo("Content Storage:")
                echo("  Format: ${stats.storageFormat}")
                echo("  Content records: ${stats.totalContentRecords}")
                if (stats.totalContentSizeBytes > 0) {
                    echo("  Total size: ${formatSize(stats.totalContentSizeBytes)}")
                }
                echo()

                stats.oldestTimestamp?.let {
                    val oldest = java.time.Instant.ofEpochMilli(it)
                        .atZone(java.time.ZoneId.systemDefault())
                        .format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE)
                    echo("  Oldest record: $oldest")
                }

                stats.newestTimestamp?.let {
                    val newest = java.time.Instant.ofEpochMilli(it)
                        .atZone(java.time.ZoneId.systemDefault())
                        .format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE)
                    echo("  Newest record: $newest")
                }
                echo()

                // Show reference map stats
                echo("Reference Analysis:")
                val refMap = f.buildContentReferenceMap()
                echo("  Content IDs with references: ${refMap.size}")
                val totalRefs = refMap.values.sumOf { it.size }
                echo("  Total references: $totalRefs")
            }
        } catch (e: Exception) {
            echo("Error: ${e.message}")
            e.printStackTrace()
        }
    }

    private fun formatSize(bytes: Long): String {
        return when {
            bytes < 1024 -> "$bytes B"
            bytes < 1024 * 1024 -> "${bytes / 1024} KB"
            bytes < 1024 * 1024 * 1024 -> "${bytes / (1024 * 1024)} MB"
            else -> "${bytes / (1024 * 1024 * 1024)} GB"
        }
    }
}

class FacadeOrphanScanCommand : CliktCommand(
    name = "facade-orphans",
    help = "Scan for orphaned content using the facade API (improved reference detection)"
) {
    private val localHistoryDir by option("-d", "--dir", help = "LocalHistory directory")
        .path()
        .default(getDefaultLocalHistoryDir())

    private val cachesDir by option("-c", "--caches", help = "IntelliJ caches directory")
        .path()
        .default(getDefaultCachesDir())

    private val minConfidence by option("--confidence", help = "Minimum orphan confidence (0.0-1.0)")
        .float()
        .default(0.7f)

    private val limit by option("-n", "--limit", help = "Maximum results to show")
        .int()
        .default(50)

    private val showStats by option("--stats", help = "Show detailed statistics")
        .flag(default = true)

    override fun run() {
        echo("Scanning for orphaned content using facade API...")
        echo()

        try {
            val detector = FacadeOrphanDetector(localHistoryDir, cachesDir)
            echo("Facade info: ${detector.getFacadeInfo()}")
            echo()

            // Build reference map
            echo("Building reference map from LocalHistory...")
            val refMap = detector.buildReferenceMap()
            echo("Found ${refMap.size} content items with references")
            echo()

            // Get all content IDs
            val contentIds = try {
                ContentStorageReader.open(cachesDir).use { reader ->
                    reader.listContentIds()
                }
            } catch (e: Exception) {
                echo("Error reading content storage: ${e.message}")
                return
            }

            echo("Scanning ${contentIds.size} content records...")

            // Find orphans
            val orphans = detector.findOrphanedContent(contentIds, minConfidence)

            if (showStats) {
                val report = detector.analyzeOrphanPatterns(contentIds)
                echo()
                echo("=== Orphan Analysis Report ===")
                echo("Total content items: ${report.totalContent}")
                echo("Reference map entries: ${report.referenceMapSize}")
                echo()
                echo("Status breakdown:")
                echo("  Active: ${report.activeCount} (${String.format("%.1f", report.activePercentage)}%)")
                echo("  Orphaned: ${report.orphanedCount} (${String.format("%.1f", report.orphanPercentage)}%)")
                echo("  Uncertain: ${report.uncertainCount}")

                if (report.uncertainByConfidence.isNotEmpty()) {
                    echo()
                    echo("Uncertain by confidence:")
                    report.uncertainByConfidence.forEach { (level, count) ->
                        echo("  $level: $count")
                    }
                }
            }

            echo()
            echo("-".repeat(80))
            echo("Orphan candidates (${orphans.size} found, showing up to $limit):")
            echo("-".repeat(80))

            for ((contentId, status) in orphans.take(limit)) {
                echo()
                echo("Content ID: $contentId")
                echo("  Status: $status")

                val details = detector.getOrphanDetails(contentId)
                details.lastReferencePath?.let { echo("  Last path: $it") }
                details.lastReferenceTime?.let {
                    val timeStr = it.atZone(java.time.ZoneId.systemDefault())
                        .format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE_TIME)
                    echo("  Last seen: $timeStr")
                }
                details.contentSize?.let { echo("  Size: $it bytes") }
            }

            if (orphans.size > limit) {
                echo()
                echo("... and ${orphans.size - limit} more orphan candidates")
            }

            detector.close()
        } catch (e: Exception) {
            echo("Error: ${e.message}")
            e.printStackTrace()
        }
    }
}

fun main(args: Array<String>) = LocalHistoryTool()
    .subcommands(
        SearchCommand(),
        ListCommand(),
        InfoCommand(),
        ContentInfoCommand(),
        ReadContentCommand(),
        RecoverCommand(),
        FindDeletedCommand(),
        AnalyzeDeletionsCommand(),
        AnalyzePatternsCommand(),
        ExportLLMCommand(),
        CacheCommand(),
        OrphanAnalyzeCommand(),
        OrphanCheckCommand(),
        OrphanCleanCommand(),
        ScanOrphansCommand(),
        // New facade-based commands
        FacadeSearchCommand(),
        FacadeListCommand(),
        FacadeStatsCommand(),
        FacadeOrphanScanCommand()
    )
    .main(args)
