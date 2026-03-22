package com.stapler.localhistory.cli.commands

import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.parameters.arguments.argument
import com.github.ajalt.clikt.parameters.options.default
import com.github.ajalt.clikt.parameters.options.flag
import com.github.ajalt.clikt.parameters.options.option
import com.github.ajalt.clikt.parameters.types.choice
import com.github.ajalt.clikt.parameters.types.float
import com.github.ajalt.clikt.parameters.types.int
import com.github.ajalt.clikt.parameters.types.path
import com.stapler.localhistory.ContentStorageReader
import com.stapler.localhistory.analyzer.FacadeOrphanDetector
import com.stapler.localhistory.getDefaultCachesDir
import com.stapler.localhistory.model.ChangeFilter
import com.stapler.localhistory.model.ChangeType
import com.stapler.localhistory.facade.LocalHistoryFacadeFactory
import com.stapler.localhistory.parser.formatSize
import com.stapler.localhistory.parser.getDefaultLocalHistoryDir
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * Search LocalHistory using the facade API (improved format support).
 */
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
                        .atZone(ZoneId.systemDefault())
                        .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)

                    echo(timestampStr)
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

/**
 * List recent changes using the facade API (improved format support).
 */
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
                        .atZone(ZoneId.systemDefault())
                        .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)

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

/**
 * Show LocalHistory statistics using the facade API.
 */
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
                        .atZone(ZoneId.systemDefault())
                        .format(DateTimeFormatter.ISO_LOCAL_DATE)
                    echo("  Oldest record: $oldest")
                }

                stats.newestTimestamp?.let {
                    val newest = java.time.Instant.ofEpochMilli(it)
                        .atZone(ZoneId.systemDefault())
                        .format(DateTimeFormatter.ISO_LOCAL_DATE)
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
}

/**
 * Scan for orphaned content using the facade API (improved reference detection).
 */
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
                    val timeStr = it.atZone(ZoneId.systemDefault())
                        .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
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
