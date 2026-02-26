package com.stapler.localhistory.facade

import com.stapler.localhistory.ContentStorageReader
import com.stapler.localhistory.model.Change
import com.stapler.localhistory.model.ChangeFilter
import com.stapler.localhistory.model.ChangeSet
import com.stapler.localhistory.model.ChangeType
import com.stapler.localhistory.model.ContentRecord
import com.stapler.localhistory.model.LocalHistoryStats
import com.stapler.localhistory.parser.VarIntReader
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Path
import kotlin.io.path.exists
import kotlin.io.path.readBytes

/**
 * LocalHistory facade implementation using custom parsing
 *
 * This is the fallback implementation that parses LocalHistory storage
 * directly without relying on IntelliJ APIs. It handles format variations
 * by being more flexible in parsing.
 */
class CustomParserLocalHistoryFacade : LocalHistoryFacade {

    private var localHistoryPath: Path? = null
    private var cachesPath: Path? = null
    private var initialized = false

    // Cached data
    private var changeSets: List<ChangeSet>? = null
    private var contentReferenceMap: Map<Int, List<Change>>? = null

    // Storage format constants
    companion object {
        private const val HEADER_SIZE = 32
        private const val RECORD_SIZE = 32
    }

    override fun initialize(localHistoryPath: Path, cachesPath: Path) {
        this.localHistoryPath = localHistoryPath
        this.cachesPath = cachesPath

        val indexPath = localHistoryPath.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryPath.resolve("changes.storageData")

        if (!indexPath.exists() || !dataPath.exists()) {
            throw IllegalArgumentException("LocalHistory files not found in $localHistoryPath")
        }

        initialized = true
    }

    override fun getChangeSets(filter: ChangeFilter): List<ChangeSet> {
        checkInitialized()

        val allChangeSets = changeSets ?: loadChangeSets().also { changeSets = it }

        return allChangeSets
            .filter { cs ->
                val afterOk = filter.afterTimestamp?.let { cs.timestamp >= it } ?: true
                val beforeOk = filter.beforeTimestamp?.let { cs.timestamp <= it } ?: true
                val pathOk = filter.pathContains?.let { term ->
                    cs.changes.any { it.path?.contains(term, ignoreCase = true) == true }
                } ?: true
                val typeOk = filter.changeTypes?.let { types ->
                    cs.changes.any { it.type in types }
                } ?: true
                val projectOk = filter.projectPath?.let { projPath ->
                    cs.changes.any { it.path?.contains(projPath) == true }
                } ?: true

                afterOk && beforeOk && pathOk && typeOk && projectOk
            }
            .take(filter.limit)
    }

    override fun searchByPath(searchTerm: String, limit: Int): List<Pair<ChangeSet, Change>> {
        checkInitialized()

        val results = mutableListOf<Pair<ChangeSet, Change>>()
        val allChangeSets = changeSets ?: loadChangeSets().also { changeSets = it }

        for (cs in allChangeSets) {
            for (change in cs.changes) {
                if (change.path?.contains(searchTerm, ignoreCase = true) == true) {
                    results.add(cs to change)
                    if (results.size >= limit) {
                        return results
                    }
                }
            }
        }

        return results
    }

    override fun getContent(contentId: Int): ContentRecord? {
        checkInitialized()

        return try {
            ContentStorageReader.open(cachesPath!!).use { reader ->
                val record = reader.readContent(contentId)
                if (record != null) {
                    ContentRecord(
                        contentId = record.contentId,
                        hash = record.cryptoHashHex,
                        content = record.content,
                        isCompressed = record.isCompressed,
                        uncompressedSize = record.uncompressedSize
                    )
                } else {
                    null
                }
            }
        } catch (e: Exception) {
            null
        }
    }

    override fun listContentIds(): List<Int> {
        checkInitialized()

        return try {
            ContentStorageReader.open(cachesPath!!).use { reader ->
                reader.listContentIds()
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    override fun getStats(): LocalHistoryStats {
        checkInitialized()

        val allChangeSets = changeSets ?: loadChangeSets().also { changeSets = it }
        val contentIds = listContentIds()

        val timestamps = allChangeSets.map { it.timestamp }.filter { it > 0 }

        return LocalHistoryStats(
            totalChangeSets = allChangeSets.size,
            totalChanges = allChangeSets.sumOf { it.changes.size },
            totalContentRecords = contentIds.size,
            oldestTimestamp = timestamps.minOrNull(),
            newestTimestamp = timestamps.maxOrNull(),
            totalContentSizeBytes = 0L,  // Don't calculate for performance
            storageFormat = ContentStorageReader.detectFormat(cachesPath!!)?.name ?: "Unknown"
        )
    }

    override fun buildContentReferenceMap(): Map<Int, List<Change>> {
        checkInitialized()

        contentReferenceMap?.let { return it }

        val map = mutableMapOf<Int, MutableList<Change>>()
        val allChangeSets = changeSets ?: loadChangeSets().also { changeSets = it }

        for (cs in allChangeSets) {
            for (change in cs.changes) {
                change.contentId?.let { contentId ->
                    map.computeIfAbsent(contentId) { mutableListOf() }
                        .add(change.copy(timestamp = cs.timestamp))
                }
            }
        }

        return map.also { contentReferenceMap = it }
    }

    override fun isReady(): Boolean = initialized

    override fun getImplementationType(): String = "Custom Parser"

    override fun close() {
        changeSets = null
        contentReferenceMap = null
        initialized = false
    }

    // Private implementation

    private fun checkInitialized() {
        if (!initialized) {
            throw IllegalStateException("Facade not initialized. Call initialize() first.")
        }
    }

    private fun loadChangeSets(): List<ChangeSet> {
        val indexPath = localHistoryPath!!.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryPath!!.resolve("changes.storageData")

        val records = readIndexFile(indexPath)
        return readDataFile(dataPath, records)
    }

    private fun readIndexFile(indexPath: Path): List<IndexRecord> {
        val data = indexPath.readBytes()
        val buf = ByteBuffer.wrap(data).order(ByteOrder.BIG_ENDIAN)

        // Read header info
        val magic = buf.getInt(0)
        val version = buf.getInt(4)

        val records = mutableListOf<IndexRecord>()
        val numRecords = (data.size - HEADER_SIZE) / RECORD_SIZE

        for (i in 1..numRecords) {
            val recordOffset = HEADER_SIZE + (i - 1) * RECORD_SIZE

            val address = buf.getLong(recordOffset)
            val size = buf.getInt(recordOffset + 8)
            val capacity = buf.getInt(recordOffset + 12)
            val prevRecord = buf.getInt(recordOffset + 16)
            val nextRecord = buf.getInt(recordOffset + 20)
            val timestamp = buf.getLong(recordOffset + 24)

            if (size > 0) {
                records.add(IndexRecord(i, address, size, capacity, prevRecord, nextRecord, timestamp))
            }
        }

        return records
    }

    private fun readDataFile(dataPath: Path, records: List<IndexRecord>): List<ChangeSet> {
        val data = dataPath.readBytes()
        val changeSets = mutableListOf<ChangeSet>()

        for (record in records) {
            if (record.address > 0 && record.size > 0 &&
                record.address + record.size <= data.size) {
                try {
                    val recordData = data.sliceArray(
                        record.address.toInt() until (record.address + record.size).toInt()
                    )
                    // Try multiple parsing strategies
                    val changeSet = tryParseChangeSet(recordData, record.timestamp, record.id)
                    if (changeSet != null) {
                        changeSets.add(changeSet)
                    }
                } catch (e: Exception) {
                    // Skip corrupted records
                }
            }
        }

        return changeSets.sortedByDescending { it.timestamp }
    }

    /**
     * Try multiple parsing strategies to handle format variations
     */
    private fun tryParseChangeSet(data: ByteArray, recordTimestamp: Long, recordId: Int): ChangeSet? {
        // Strategy 1: Standard format
        parseChangeSetStandard(data, recordTimestamp)?.let { return it }

        // Strategy 2: Try with different version handling
        parseChangeSetAlternate(data, recordTimestamp)?.let { return it }

        // Strategy 3: Minimal parse - just get what we can
        return parseChangeSetMinimal(data, recordTimestamp, recordId)
    }

    private fun parseChangeSetStandard(data: ByteArray, recordTimestamp: Long): ChangeSet? {
        return try {
            val reader = FlexibleVarIntReader(data)

            val version = reader.readVarInt()
            if (version < 0 || version > 10) return null  // Invalid version

            val id = reader.readVarLong()
            val name = reader.readStringOrNull()
            val timestamp = reader.readVarLong()
            val effectiveTimestamp = if (timestamp > 0) timestamp else recordTimestamp

            // Activity info (version >= 1)
            var activityId: String? = null
            var activityProvider: String? = null
            if (version >= 1) {
                activityId = reader.readStringOrNull()
                activityProvider = reader.readStringOrNull()
            }

            val changeCount = reader.readVarInt()
            if (changeCount < 0 || changeCount > 10000) return null  // Sanity check

            val changes = mutableListOf<Change>()
            repeat(changeCount) {
                try {
                    parseChange(reader)?.let { changes.add(it) }
                } catch (e: Exception) {
                    // Skip unparseable change
                }
            }

            ChangeSet(id, name, effectiveTimestamp, changes, activityId, activityProvider)
        } catch (e: Exception) {
            null
        }
    }

    private fun parseChangeSetAlternate(data: ByteArray, recordTimestamp: Long): ChangeSet? {
        return try {
            val reader = FlexibleVarIntReader(data)

            // Skip first byte if it looks like a flag
            val firstByte = data[0].toInt() and 0xFF
            if (firstByte > 10) {
                reader.skip(1)
            }

            val version = reader.readVarInt()
            val id = reader.readVarLong()
            val name = reader.readStringOrNull()
            val timestamp = reader.readVarLong()
            val effectiveTimestamp = if (timestamp > 0) timestamp else recordTimestamp

            if (version >= 1) {
                reader.readStringOrNull()  // activity id
                reader.readStringOrNull()  // activity provider
            }

            val changeCount = reader.readVarInt()
            if (changeCount < 0 || changeCount > 10000) return null

            val changes = mutableListOf<Change>()
            repeat(changeCount) {
                try {
                    parseChange(reader)?.let { changes.add(it) }
                } catch (e: Exception) {
                    // Skip
                }
            }

            ChangeSet(id, name, effectiveTimestamp, changes, null, null)
        } catch (e: Exception) {
            null
        }
    }

    private fun parseChangeSetMinimal(data: ByteArray, recordTimestamp: Long, recordId: Int): ChangeSet? {
        // Last resort - create a minimal change set from available data
        return ChangeSet(
            id = recordId.toLong(),
            name = null,
            timestamp = recordTimestamp,
            changes = emptyList(),
            activityId = null,
            activityProvider = null
        )
    }

    private fun parseChange(reader: FlexibleVarIntReader): Change? {
        val typeId = reader.readVarInt()
        val changeType = ChangeType.fromId(typeId)

        var path: String? = null
        var contentId: Int? = null
        var oldPath: String? = null

        when (typeId) {
            in 1..7 -> {
                reader.readVarLong()  // change id
                path = reader.readString()

                if (typeId == 3) {  // ContentChange
                    contentId = reader.readVarInt()
                    reader.readVarLong()  // old timestamp
                }

                if (typeId == 4 || typeId == 6) {  // Rename or Move
                    oldPath = try { reader.readString() } catch (e: Exception) { null }
                }
            }
            8, 9 -> {  // Label changes
                reader.readVarLong()
                reader.readStringOrNull()
            }
        }

        return Change(changeType, path, contentId, oldPath)
    }

    // Internal data classes

    private data class IndexRecord(
        val id: Int,
        val address: Long,
        val size: Int,
        val capacity: Int,
        val prevRecord: Int,
        val nextRecord: Int,
        val timestamp: Long
    )

    /**
     * Flexible variable-length integer reader with error recovery
     */
    private class FlexibleVarIntReader(private val data: ByteArray, private var offset: Int = 0) {

        fun skip(count: Int) {
            offset += count
        }

        fun hasMore(): Boolean = offset < data.size

        fun readVarInt(): Int {
            if (offset >= data.size) return 0

            val b = data[offset].toInt() and 0xFF
            return when {
                b >= 192 -> {
                    offset += 2
                    if (offset > data.size) return 0
                    ((b - 192) shl 8) or (data[offset - 1].toInt() and 0xFF)
                }
                b >= 128 -> {
                    offset++
                    b - 128
                }
                b >= 64 -> {
                    offset += 4
                    if (offset > data.size) return 0
                    ((b - 64) shl 24) or
                        ((data[offset - 3].toInt() and 0xFF) shl 16) or
                        ((data[offset - 2].toInt() and 0xFF) shl 8) or
                        (data[offset - 1].toInt() and 0xFF)
                }
                b >= 32 -> {
                    offset += 3
                    if (offset > data.size) return 0
                    ((b - 32) shl 16) or
                        ((data[offset - 2].toInt() and 0xFF) shl 8) or
                        (data[offset - 1].toInt() and 0xFF)
                }
                b == 31 -> {
                    offset += 5
                    if (offset > data.size) return 0
                    ByteBuffer.wrap(data, offset - 4, 4).order(ByteOrder.BIG_ENDIAN).int
                }
                else -> {
                    offset++
                    b
                }
            }
        }

        fun readVarLong(): Long = readVarInt().toLong()

        fun readString(): String {
            val length = readVarInt()
            if (length == 0) return ""
            if (offset + length > data.size) return ""
            val str = String(data, offset, length, Charsets.UTF_8)
            offset += length
            return str
        }

        fun readStringOrNull(): String? {
            if (offset >= data.size) return null
            val hasValue = data[offset++].toInt() != 0
            return if (hasValue) readString() else null
        }
    }
}
