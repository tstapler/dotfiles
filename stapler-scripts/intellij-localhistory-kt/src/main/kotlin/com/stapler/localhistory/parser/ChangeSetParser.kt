package com.stapler.localhistory.parser

import com.stapler.localhistory.model.IndexRecord
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Path
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.io.path.readBytes

/**
 * Storage format constants from LocalHistoryRecordsTable.java
 */
object StorageConstants {
    const val DEFAULT_HEADER_SIZE = 8  // magic(4) + version(4)
    const val LAST_ID_OFFSET = DEFAULT_HEADER_SIZE  // 8
    const val FIRST_RECORD_OFFSET = LAST_ID_OFFSET + 8  // 16
    const val LAST_RECORD_OFFSET = FIRST_RECORD_OFFSET + 4  // 20
    const val FS_TIMESTAMP_OFFSET = LAST_RECORD_OFFSET + 4  // 24
    const val HEADER_SIZE = FS_TIMESTAMP_OFFSET + 8  // 32

    // Record format from AbstractRecordsTable + LocalHistoryRecordsTable
    const val DEFAULT_RECORD_SIZE = 16  // address(8) + size(4) + capacity(4)
    const val PREV_RECORD_OFFSET = DEFAULT_RECORD_SIZE  // 16
    const val NEXT_RECORD_OFFSET = PREV_RECORD_OFFSET + 4  // 20
    const val TIMESTAMP_OFFSET = NEXT_RECORD_OFFSET + 4  // 24
    const val RECORD_SIZE = TIMESTAMP_OFFSET + 8  // 32
}

/**
 * Change types from DataStreamUtil.java
 */
val CHANGE_TYPES = mapOf(
    1 to "CreateFile",
    2 to "CreateDirectory",
    3 to "ContentChange",
    4 to "Rename",
    5 to "ROStatusChange",
    6 to "Move",
    7 to "Delete",
    8 to "PutLabel",
    9 to "PutSystemLabel"
)

/**
 * Legacy data classes for backward compatibility with existing parsing code.
 * These map to the unified model types but keep the old API.
 */
data class ChangeInfo(
    val changeType: String,
    val path: String?,
    val contentId: Int?
)

data class ChangeSetInfo(
    val id: Long,
    val name: String?,
    val timestamp: Long,
    val changes: List<ChangeInfo>
) {
    val timestampStr: String
        get() = if (timestamp > 0) {
            Instant.ofEpochMilli(timestamp)
                .atZone(ZoneId.systemDefault())
                .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
        } else "N/A"
}

/**
 * Parse a change set from raw record data.
 */
fun parseChangeSet(data: ByteArray): ChangeSetInfo? {
    return try {
        val reader = VarIntReader(data)
        val version = reader.readVarInt()
        val id = reader.readVarLong()
        val name = reader.readStringOrNull()
        val timestamp = reader.readVarLong()

        // Activity ID (version >= 1)
        if (version >= 1) {
            reader.readStringOrNull()  // kind
            reader.readStringOrNull()  // provider
        }

        val changeCount = reader.readVarInt()
        val changes = mutableListOf<ChangeInfo>()

        repeat(changeCount) {
            try {
                val changeTypeId = reader.readVarInt()
                val changeType = CHANGE_TYPES[changeTypeId] ?: "Unknown($changeTypeId)"

                var path: String? = null
                var contentId: Int? = null

                // Structural changes have id + path
                if (changeTypeId in 1..7) {
                    reader.readVarLong()  // change id
                    path = reader.readString()

                    // ContentChange has content + timestamp
                    if (changeTypeId == 3) {
                        contentId = reader.readVarInt()
                        reader.readVarLong()  // old timestamp
                    }

                    // CreateFile/CreateDirectory have additional entry data
                    if (changeTypeId in 1..2) {
                        // Skip entry data - format varies
                    }
                }

                changes.add(ChangeInfo(changeType, path, contentId))
            } catch (e: Exception) {
                // Stop parsing on error
            }
        }

        ChangeSetInfo(id, name, timestamp, changes)
    } catch (e: Exception) {
        null
    }
}

/**
 * Parse the index file and return header info and records.
 */
fun parseIndexFile(indexPath: Path): Pair<Map<String, Any>, List<IndexRecord>> {
    val data = indexPath.readBytes()
    val buf = ByteBuffer.wrap(data).order(ByteOrder.BIG_ENDIAN)

    val magic = buf.getInt(0)
    val version = buf.getInt(4)
    val lastId = buf.getLong(StorageConstants.LAST_ID_OFFSET)
    val firstRecord = buf.getInt(StorageConstants.FIRST_RECORD_OFFSET)
    val lastRecord = buf.getInt(StorageConstants.LAST_RECORD_OFFSET)
    val fsTimestamp = buf.getLong(StorageConstants.FS_TIMESTAMP_OFFSET)

    val header = mapOf(
        "magic" to "0x${magic.toString(16)}",
        "version" to version,
        "lastId" to lastId,
        "firstRecord" to firstRecord,
        "lastRecord" to lastRecord,
        "fsTimestamp" to fsTimestamp
    )

    val records = mutableListOf<IndexRecord>()
    val numRecords = (data.size - StorageConstants.HEADER_SIZE) / StorageConstants.RECORD_SIZE

    for (i in 1..numRecords) {
        val recordOffset = StorageConstants.HEADER_SIZE + (i - 1) * StorageConstants.RECORD_SIZE

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

    return header to records
}

/**
 * Parse the data file using the index records.
 */
fun parseDataFile(dataPath: Path, records: List<IndexRecord>): Map<Int, ChangeSetInfo?> {
    val data = dataPath.readBytes()
    return records.associate { record ->
        val changeSet = if (record.address > 0 && record.size > 0 &&
                           record.address + record.size <= data.size) {
            val recordData = data.sliceArray(record.address.toInt() until (record.address + record.size).toInt())
            parseChangeSet(recordData)
        } else null
        record.id to changeSet
    }
}

/**
 * Get the default LocalHistory directory for the current user.
 */
fun getDefaultLocalHistoryDir(): Path {
    val home = System.getProperty("user.home")
    val cacheDir = Path.of(home, "Library/Caches/JetBrains")

    // Find the most recent IntelliJ version
    val ideaDirs = cacheDir.toFile().listFiles { file ->
        file.isDirectory && file.name.startsWith("IntelliJIdea")
    }?.sortedByDescending { it.lastModified() }

    return ideaDirs?.firstOrNull()?.let {
        Path.of(it.absolutePath, "LocalHistory")
    } ?: Path.of(home, "Library/Caches/JetBrains/IntelliJIdea2025.2/LocalHistory")
}

/**
 * Format a byte size for display.
 */
fun formatSize(bytes: Long): String {
    return when {
        bytes < 1024 -> "$bytes B"
        bytes < 1024 * 1024 -> "${bytes / 1024} KB"
        bytes < 1024 * 1024 * 1024 -> "${bytes / (1024 * 1024)} MB"
        else -> "${bytes / (1024 * 1024 * 1024)} GB"
    }
}
