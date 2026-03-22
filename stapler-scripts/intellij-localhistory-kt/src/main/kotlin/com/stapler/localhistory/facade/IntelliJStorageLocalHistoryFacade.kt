package com.stapler.localhistory.facade

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
 * LocalHistory facade implementation using IntelliJ's storage APIs
 *
 * This implementation uses IntelliJ's AbstractStorage and related classes
 * to read LocalHistory data in a way that's compatible with format changes.
 */
class IntelliJStorageLocalHistoryFacade : LocalHistoryFacade {

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

        // Change type IDs from IntelliJ source
        private val CHANGE_TYPE_MAP = mapOf(
            1 to ChangeType.CREATE_FILE,
            2 to ChangeType.CREATE_DIRECTORY,
            3 to ChangeType.CONTENT_CHANGE,
            4 to ChangeType.RENAME,
            5 to ChangeType.RO_STATUS_CHANGE,
            6 to ChangeType.MOVE,
            7 to ChangeType.DELETE,
            8 to ChangeType.PUT_LABEL,
            9 to ChangeType.PUT_SYSTEM_LABEL
        )
    }

    override fun initialize(localHistoryPath: Path, cachesPath: Path) {
        this.localHistoryPath = localHistoryPath
        this.cachesPath = cachesPath

        // Verify paths exist
        val indexPath = localHistoryPath.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryPath.resolve("changes.storageData")

        if (!indexPath.exists() || !dataPath.exists()) {
            throw IllegalArgumentException("LocalHistory files not found in $localHistoryPath")
        }

        initialized = true
    }

    override fun getChangeSets(filter: ChangeFilter): List<ChangeSet> {
        checkInitialized()

        // Use cached data if available
        val allChangeSets = changeSets ?: loadChangeSets().also { changeSets = it }

        return allChangeSets
            .filter { cs ->
                // Apply filters
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
            readContentFromStorage(contentId)
        } catch (e: Exception) {
            null
        }
    }

    override fun listContentIds(): List<Int> {
        checkInitialized()

        return try {
            val contentStorage = findContentStorage()
            if (contentStorage != null) {
                readContentIdsFromStorage(contentStorage)
            } else {
                emptyList()
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
            totalContentSizeBytes = calculateTotalContentSize(),
            storageFormat = detectStorageFormat()
        )
    }

    override fun buildContentReferenceMap(): Map<Int, List<Change>> {
        checkInitialized()

        // Use cached data if available
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

    override fun getImplementationType(): String = "IntelliJ Storage API"

    override fun close() {
        changeSets = null
        contentReferenceMap = null
        initialized = false
    }

    // Private implementation methods

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
                    val changeSet = parseChangeSet(recordData, record.timestamp)
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

    private fun parseChangeSet(data: ByteArray, recordTimestamp: Long): ChangeSet? {
        return try {
            val reader = VarIntReader(data)

            // Read version
            val version = reader.readVarInt()

            // Sanity check: version should be small
            if (version < 0 || version > 20) {
                return null
            }

            // Read changeset ID
            val id = reader.readVarLong()

            // Read name (nullable string)
            val name = reader.readStringOrNull()

            // Read timestamp
            val timestamp = reader.readVarLong()
            val effectiveTimestamp = if (timestamp > 0) timestamp else recordTimestamp

            // Activity info (version >= 1)
            var activityId: String? = null
            var activityProvider: String? = null
            if (version >= 1) {
                activityId = reader.readStringOrNull()
                activityProvider = reader.readStringOrNull()
            }

            // Read change count with sanity check
            val changeCount = reader.readVarInt()

            // Sanity check: change count should be reasonable
            if (changeCount < 0 || changeCount > 10000) {
                return null
            }

            val changes = mutableListOf<Change>()

            repeat(changeCount) {
                try {
                    val change = parseChange(reader, version)
                    if (change != null) {
                        changes.add(change)
                    }
                } catch (e: Exception) {
                    // Skip unparseable changes
                }
            }

            ChangeSet(
                id = id,
                name = name,
                timestamp = effectiveTimestamp,
                changes = changes,
                activityId = activityId,
                activityProvider = activityProvider
            )
        } catch (e: Exception) {
            null
        }
    }

    private fun parseChange(reader: VarIntReader, version: Int): Change? {
        val typeId = reader.readVarInt()
        val changeType = CHANGE_TYPE_MAP[typeId] ?: ChangeType.UNKNOWN

        var path: String? = null
        var contentId: Int? = null
        var oldPath: String? = null

        when (typeId) {
            in 1..7 -> {
                // Structural changes have id + path
                reader.readVarLong()  // change id
                path = reader.readString()

                // ContentChange has content + timestamp
                if (typeId == 3) {
                    contentId = reader.readVarInt()
                    reader.readVarLong()  // old timestamp
                }

                // Rename/Move have old path
                if (typeId == 4 || typeId == 6) {
                    oldPath = try { reader.readString() } catch (e: Exception) { null }
                }
            }
            8, 9 -> {
                // Label changes
                reader.readVarLong()  // label id
                reader.readStringOrNull()  // label name
            }
        }

        return Change(
            type = changeType,
            path = path,
            contentId = contentId,
            oldPath = oldPath
        )
    }

    private fun findContentStorage(): Path? {
        val cachesPath = this.cachesPath ?: return null

        // Try different possible locations
        val candidates = listOf(
            cachesPath.resolve("content.dat"),
            cachesPath.resolve("caches/content.dat"),
            cachesPath.resolve("LocalHistory/content.dat")
        )

        return candidates.firstOrNull { it.exists() }
    }

    private fun readContentFromStorage(contentId: Int): ContentRecord? {
        // Use the existing ContentStorageReader if available
        val cachesPath = this.cachesPath ?: return null

        return try {
            com.stapler.localhistory.ContentStorageReader.open(cachesPath).use { reader ->
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

    private fun readContentIdsFromStorage(storagePath: Path): List<Int> {
        val cachesPath = this.cachesPath ?: return emptyList()

        return try {
            com.stapler.localhistory.ContentStorageReader.open(cachesPath).use { reader ->
                reader.listContentIds()
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    private fun calculateTotalContentSize(): Long {
        val cachesPath = this.cachesPath ?: return 0L

        return try {
            com.stapler.localhistory.ContentStorageReader.open(cachesPath).use { reader ->
                reader.listContentIds().sumOf { id ->
                    reader.readContent(id)?.content?.size?.toLong() ?: 0L
                }
            }
        } catch (e: Exception) {
            0L
        }
    }

    private fun detectStorageFormat(): String {
        val cachesPath = this.cachesPath ?: return "Unknown"

        return try {
            com.stapler.localhistory.ContentStorageReader.detectFormat(cachesPath)?.name
                ?: "Unknown"
        } catch (e: Exception) {
            "Unknown"
        }
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
}
