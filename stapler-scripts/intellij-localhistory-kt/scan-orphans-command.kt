// ScanOrphansCommand implementation to add to Main.kt

import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.parameters.options.choice
import com.github.ajalt.clikt.parameters.options.default
import com.github.ajalt.clikt.parameters.options.flag
import com.github.ajalt.clikt.parameters.options.option
import com.github.ajalt.clikt.parameters.types.float
import com.github.ajalt.clikt.parameters.types.int
import com.github.ajalt.clikt.parameters.types.path
import com.stapler.localhistory.analyzer.*
import com.stapler.localhistory.*
import java.nio.file.Path
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.math.roundToInt

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