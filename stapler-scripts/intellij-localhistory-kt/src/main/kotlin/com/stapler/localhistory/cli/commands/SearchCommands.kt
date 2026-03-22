package com.stapler.localhistory.cli.commands

import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.parameters.arguments.argument
import com.github.ajalt.clikt.parameters.options.default
import com.github.ajalt.clikt.parameters.options.option
import com.github.ajalt.clikt.parameters.types.int
import com.github.ajalt.clikt.parameters.types.path
import com.stapler.localhistory.parser.getDefaultLocalHistoryDir
import com.stapler.localhistory.parser.parseDataFile
import com.stapler.localhistory.parser.parseIndexFile
import kotlin.io.path.exists
import kotlin.io.path.readBytes

/**
 * Search for files in LocalHistory.
 */
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

        val matches = mutableListOf<Triple<com.stapler.localhistory.model.IndexRecord, com.stapler.localhistory.parser.ChangeSetInfo, com.stapler.localhistory.parser.ChangeInfo>>()
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

/**
 * List recent changes.
 */
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

/**
 * Show LocalHistory info.
 */
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
        val cachesDir = com.stapler.localhistory.getDefaultCachesDir()
        echo("  Caches directory: $cachesDir")
        val format = com.stapler.localhistory.ContentStorageReader.detectFormat(cachesDir)
        echo("  Storage format: ${format ?: "Not found"}")
        if (format != null) {
            try {
                com.stapler.localhistory.ContentStorageReader.open(cachesDir).use { reader ->
                    echo("  Record count: ${reader.getRecordCount()}")
                }
            } catch (e: Exception) {
                echo("  Error: ${e.message}")
            }
        }
    }
}
