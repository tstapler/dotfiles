package com.stapler.localhistory.debug

import com.stapler.localhistory.parser.VarIntReader
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Path
import kotlin.io.path.readBytes

/**
 * Diagnostic tool for analyzing IntelliJ LocalHistory storage format
 */
class FormatAnalyzer(private val localHistoryPath: Path) {

    fun analyzeIndexFile(): IndexAnalysis {
        val indexPath = localHistoryPath.resolve("changes.storageRecordIndex")
        val data = indexPath.readBytes()
        val buf = ByteBuffer.wrap(data).order(ByteOrder.BIG_ENDIAN)

        // Read header
        val magic = buf.getInt(0)
        val version = buf.getInt(4)
        val lastId = buf.getLong(8)
        val firstRecord = buf.getInt(16)
        val lastRecord = buf.getInt(20)
        val fsTimestamp = buf.getLong(24)

        // Count records
        val headerSize = 32
        val recordSize = 32
        val numRecords = (data.size - headerSize) / recordSize

        val records = mutableListOf<RecordInfo>()
        for (i in 1..numRecords) {
            val offset = headerSize + (i - 1) * recordSize
            val address = buf.getLong(offset)
            val size = buf.getInt(offset + 8)
            val capacity = buf.getInt(offset + 12)
            val prevRecord = buf.getInt(offset + 16)
            val nextRecord = buf.getInt(offset + 20)
            val timestamp = buf.getLong(offset + 24)

            if (size > 0) {
                records.add(RecordInfo(i, address, size, capacity, prevRecord, nextRecord, timestamp))
            }
        }

        return IndexAnalysis(
            magic = magic,
            version = version,
            lastId = lastId,
            firstRecord = firstRecord,
            lastRecord = lastRecord,
            fsTimestamp = fsTimestamp,
            totalRecords = numRecords,
            activeRecords = records.size,
            records = records
        )
    }

    fun analyzeDataRecords(maxRecords: Int = 10): List<DataRecordAnalysis> {
        val indexAnalysis = analyzeIndexFile()
        val dataPath = localHistoryPath.resolve("changes.storageData")
        val data = dataPath.readBytes()

        return indexAnalysis.records.take(maxRecords).map { record ->
            analyzeDataRecord(data, record)
        }
    }

    private fun analyzeDataRecord(data: ByteArray, record: RecordInfo): DataRecordAnalysis {
        if (record.address < 0 || record.address + record.size > data.size) {
            return DataRecordAnalysis(record.id, "Invalid address", emptyList(), null)
        }

        val recordData = data.sliceArray(record.address.toInt() until (record.address + record.size).toInt())

        // Analyze byte patterns
        val hexDump = recordData.take(100).joinToString(" ") { "%02x".format(it) }

        // Try to detect format version by examining first bytes
        val firstBytes = recordData.take(20).map { it.toInt() and 0xFF }

        // Try different parsing strategies
        val parseAttempts = mutableListOf<ParseAttempt>()

        // Strategy 1: Standard VarInt
        try {
            val result = parseWithStandardVarInt(recordData, record.timestamp)
            parseAttempts.add(ParseAttempt("StandardVarInt", result))
        } catch (e: Exception) {
            parseAttempts.add(ParseAttempt("StandardVarInt", "Failed: ${e.message}"))
        }

        // Strategy 2: DataInputStream style
        try {
            val result = parseWithDataInputStream(recordData, record.timestamp)
            parseAttempts.add(ParseAttempt("DataInputStream", result))
        } catch (e: Exception) {
            parseAttempts.add(ParseAttempt("DataInputStream", "Failed: ${e.message}"))
        }

        // Strategy 3: Simple integers
        try {
            val result = parseWithSimpleInts(recordData, record.timestamp)
            parseAttempts.add(ParseAttempt("SimpleInts", result))
        } catch (e: Exception) {
            parseAttempts.add(ParseAttempt("SimpleInts", "Failed: ${e.message}"))
        }

        return DataRecordAnalysis(
            recordId = record.id,
            hexDump = hexDump,
            parseAttempts = parseAttempts,
            rawFirstBytes = firstBytes
        )
    }

    private fun parseWithStandardVarInt(data: ByteArray, recordTimestamp: Long): String {
        val reader = VarIntReader(data)
        val sb = StringBuilder()

        val version = reader.readVarInt()
        sb.append("version=$version, ")

        val id = reader.readVarLong()
        sb.append("id=$id, ")

        val hasName = if (reader.hasMore()) data[reader.position()].toInt() != 0 else false
        reader.skip(1)
        val name = if (hasName && reader.hasMore()) reader.readString() else null
        sb.append("name=$name, ")

        val timestamp = reader.readVarLong()
        sb.append("timestamp=$timestamp, ")

        if (version >= 1 && reader.hasMore()) {
            val hasActivityKind = data[reader.position()].toInt() != 0
            reader.skip(1)
            if (hasActivityKind) reader.readString()

            val hasActivityProvider = if (reader.hasMore()) data[reader.position()].toInt() != 0 else false
            reader.skip(1)
            if (hasActivityProvider) reader.readString()
        }

        val changeCount = if (reader.hasMore()) reader.readVarInt() else 0
        sb.append("changeCount=$changeCount, ")

        // Try to read first change
        if (changeCount > 0 && changeCount < 1000 && reader.hasMore()) {
            val changeType = reader.readVarInt()
            sb.append("firstChangeType=$changeType")
        }

        return sb.toString()
    }

    private fun parseWithDataInputStream(data: ByteArray, recordTimestamp: Long): String {
        val buf = ByteBuffer.wrap(data).order(ByteOrder.BIG_ENDIAN)
        val sb = StringBuilder()

        // Try reading as big-endian integers
        if (data.size >= 4) {
            val firstInt = buf.getInt(0)
            sb.append("firstInt=$firstInt, ")
        }
        if (data.size >= 8) {
            val firstLong = buf.getLong(0)
            sb.append("firstLong=$firstLong, ")
        }
        if (data.size >= 12) {
            val secondInt = buf.getInt(4)
            sb.append("secondInt=$secondInt, ")
        }

        return sb.toString()
    }

    private fun parseWithSimpleInts(data: ByteArray, recordTimestamp: Long): String {
        val sb = StringBuilder()

        // Read first few bytes as unsigned
        sb.append("bytes=[")
        data.take(16).forEachIndexed { i, b ->
            if (i > 0) sb.append(", ")
            sb.append(b.toInt() and 0xFF)
        }
        sb.append("]")

        return sb.toString()
    }

    /**
     * Analyze what actual change types are in the data
     */
    fun findChangeTypePatterns(): Map<Int, Int> {
        val dataPath = localHistoryPath.resolve("changes.storageData")
        val data = dataPath.readBytes()
        val indexAnalysis = analyzeIndexFile()

        val changeTypeCounts = mutableMapOf<Int, Int>()

        for (record in indexAnalysis.records.take(100)) {
            if (record.address < 0 || record.address + record.size > data.size) continue

            val recordData = data.sliceArray(record.address.toInt() until (record.address + record.size).toInt())

            try {
                val reader = VarIntReader(recordData)

                // Skip header fields
                val version = reader.readVarInt()
                if (version < 0 || version > 20) continue

                reader.readVarLong() // id
                reader.readStringOrNull() // name
                reader.readVarLong() // timestamp

                if (version >= 1) {
                    reader.readStringOrNull() // activity kind
                    reader.readStringOrNull() // activity provider
                }

                val changeCount = reader.readVarInt()
                if (changeCount < 0 || changeCount > 10000) continue

                repeat(minOf(changeCount, 50)) {
                    if (!reader.hasMore()) return@repeat
                    val typeId = reader.readVarInt()
                    changeTypeCounts[typeId] = changeTypeCounts.getOrDefault(typeId, 0) + 1

                    // Skip rest of change based on type
                    skipChangeData(reader, typeId)
                }
            } catch (e: Exception) {
                // Skip corrupted records
            }
        }

        return changeTypeCounts.toSortedMap()
    }

    private fun skipChangeData(reader: VarIntReader, typeId: Int) {
        try {
            when (typeId) {
                in 1..7 -> {
                    reader.readVarLong() // change id
                    reader.readString() // path
                    if (typeId == 3) {
                        reader.readVarInt() // content id
                        reader.readVarLong() // old timestamp
                    }
                }
                8, 9 -> {
                    reader.readVarLong() // label id
                    reader.readStringOrNull() // label name
                }
            }
        } catch (e: Exception) {
            // Ignore
        }
    }

    data class RecordInfo(
        val id: Int,
        val address: Long,
        val size: Int,
        val capacity: Int,
        val prevRecord: Int,
        val nextRecord: Int,
        val timestamp: Long
    )

    data class IndexAnalysis(
        val magic: Int,
        val version: Int,
        val lastId: Long,
        val firstRecord: Int,
        val lastRecord: Int,
        val fsTimestamp: Long,
        val totalRecords: Int,
        val activeRecords: Int,
        val records: List<RecordInfo>
    )

    data class ParseAttempt(val strategy: String, val result: String)

    data class DataRecordAnalysis(
        val recordId: Int,
        val hexDump: String,
        val parseAttempts: List<ParseAttempt>,
        val rawFirstBytes: List<Int>?
    )
}
