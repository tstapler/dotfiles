package com.stapler.localhistory

import net.jpountz.lz4.LZ4Factory
import java.io.Closeable
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel
import java.nio.file.Path
import java.nio.file.StandardOpenOption
import java.util.zip.Inflater
import kotlin.io.path.exists
import kotlin.io.path.fileSize
import kotlin.io.path.readBytes

/**
 * PersistentFS Content Storage Reader
 *
 * Reads file content from IntelliJ's PersistentFS content.dat storage.
 * Uses IntelliJ platform utilities where possible for format compatibility.
 *
 * Supports two storage formats:
 * 1. Legacy format (IntelliJ 2023.x): content.dat.storageRecordIndex + content.dat.storageData
 * 2. Modern format (IntelliJ 2024+): content.dat (AppendOnlyLog format)
 */

// AppendOnlyLog header constants (from AppendOnlyLogOverMMappedFile.HeaderLayout)
// Magic bytes are "MLOA" (0x4d, 0x4c, 0x4f, 0x41) which reads as 0x414f4c4d in little-endian
private const val AOL_MAGIC = 0x414f4c4d
private const val AOL_HEADER_SIZE = 64    // Based on source analysis

// Content record format
private const val CONTENT_HASH_LENGTH = 20  // SHA-1 hash length

// Legacy AbstractStorage constants
private const val LEGACY_SAFELY_CLOSED_MAGIC = 0x1f2f3f4f
private const val LEGACY_HEADER_SIZE = 8  // magic(4) + version(4)
private const val LEGACY_RECORD_SIZE = 16  // address(8) + size(4) + capacity(4)

/**
 * Content record from PersistentFS
 */
data class ContentRecord(
    val contentId: Int,
    val cryptoHash: ByteArray,
    val isCompressed: Boolean,
    val uncompressedSize: Int,
    val content: ByteArray
) {
    val cryptoHashHex: String
        get() = cryptoHash.joinToString("") { "%02x".format(it) }

    fun contentAsString(charset: java.nio.charset.Charset = Charsets.UTF_8): String {
        return String(content, charset)
    }

    fun isTextContent(): Boolean {
        // Heuristic: check if content is mostly printable ASCII
        if (content.isEmpty()) return true
        val printableCount = content.count { b ->
            val i = b.toInt() and 0xFF
            i in 0x20..0x7E || i == 0x09 || i == 0x0A || i == 0x0D
        }
        return printableCount.toDouble() / content.size > 0.9
    }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is ContentRecord) return false
        return contentId == other.contentId
    }

    override fun hashCode(): Int = contentId
}

/**
 * Detects storage format version based on file magic
 */
enum class StorageFormat {
    LEGACY,           // content.dat.storageRecordIndex + content.dat.storageData
    APPEND_ONLY_LOG   // content.dat with MLOA magic
}

/**
 * Abstract content storage reader
 */
sealed class ContentStorageReader(val storagePath: Path) : Closeable {
    abstract fun readContent(contentId: Int): ContentRecord?
    abstract fun listContentIds(): List<Int>
    abstract fun getRecordCount(): Int
    abstract override fun close()

    companion object {
        fun open(cachesDir: Path): ContentStorageReader {
            // Try modern format first (content.dat)
            val modernPath = cachesDir.resolve("content.dat")
            if (modernPath.exists()) {
                val magic = readMagic(modernPath)
                if (magic == AOL_MAGIC) {
                    return AppendOnlyLogContentReader(modernPath)
                }
            }

            // Try legacy format
            val legacyIndexPath = cachesDir.resolve("content.dat.storageRecordIndex")
            val legacyDataPath = cachesDir.resolve("content.dat.storageData")
            if (legacyIndexPath.exists() && legacyDataPath.exists()) {
                return LegacyContentReader(legacyIndexPath, legacyDataPath)
            }

            throw IllegalStateException("No valid content storage found in $cachesDir")
        }

        private fun readMagic(path: Path): Int {
            FileChannel.open(path, StandardOpenOption.READ).use { channel ->
                val buf = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN)
                channel.read(buf)
                buf.flip()
                return buf.int
            }
        }

        fun detectFormat(cachesDir: Path): StorageFormat? {
            val modernPath = cachesDir.resolve("content.dat")
            if (modernPath.exists()) {
                val magic = readMagic(modernPath)
                if (magic == AOL_MAGIC) {
                    return StorageFormat.APPEND_ONLY_LOG
                }
            }

            val legacyIndexPath = cachesDir.resolve("content.dat.storageRecordIndex")
            val legacyDataPath = cachesDir.resolve("content.dat.storageData")
            if (legacyIndexPath.exists() && legacyDataPath.exists()) {
                return StorageFormat.LEGACY
            }

            return null
        }
    }
}

/**
 * Reader for modern AppendOnlyLog format (IntelliJ 2024+)
 *
 * Record format in content storage:
 * - cryptoHash[20 bytes]: SHA-1 hash of content
 * - uncompressedSize(int32): positive = uncompressed, negative = compressed (actual size = -value)
 * - content[...]: actual content bytes (possibly compressed)
 */
class AppendOnlyLogContentReader(storagePath: Path) : ContentStorageReader(storagePath) {
    private val channel: FileChannel = FileChannel.open(storagePath, StandardOpenOption.READ)
    private val fileSize: Long = storagePath.fileSize()
    private val lz4Factory = LZ4Factory.fastestInstance()

    // Header fields parsed from the file
    private val version: Int
    private val pageSize: Int = 1 shl 20  // 1MB default page size for content storage

    init {
        val headerBuf = ByteBuffer.allocate(AOL_HEADER_SIZE).order(ByteOrder.LITTLE_ENDIAN)
        channel.read(headerBuf, 0)
        headerBuf.flip()

        val magic = headerBuf.int
        if (magic != AOL_MAGIC) {
            throw IllegalStateException("Invalid magic: expected 0x${AOL_MAGIC.toString(16)}, got 0x${magic.toString(16)}")
        }

        version = headerBuf.int
    }

    override fun readContent(contentId: Int): ContentRecord? {
        try {
            // In AppendOnlyLog, recordId maps to offset via:
            // offset = ((recordId - 1) << 2) + HEADER_SIZE
            val offset = recordIdToOffset(contentId)
            if (offset < AOL_HEADER_SIZE || offset >= fileSize) {
                return null
            }

            // Read record header (4 bytes length prefix in AppendOnlyLog)
            val headerBuf = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN)
            channel.read(headerBuf, offset)
            headerBuf.flip()

            val lengthField = headerBuf.int
            val recordLength = lengthField and 0x3FFFFFFF  // Mask out top 2 bits (flags)

            if (recordLength <= 0 || recordLength > 100_000_000) {
                return null
            }

            // recordLength includes the 4-byte header, so payload is recordLength - 4
            val payloadLength = recordLength - 4

            // Verify we have enough data
            if (offset + 4 + payloadLength > fileSize) {
                return null
            }

            // Read full record payload (excludes the 4-byte length header)
            val recordBuf = ByteBuffer.allocate(payloadLength).order(ByteOrder.LITTLE_ENDIAN)
            channel.read(recordBuf, offset + 4)
            recordBuf.flip()

            // Parse record: cryptoHash[20] + uncompressedSize(int32, little-endian) + content[...]
            if (payloadLength < CONTENT_HASH_LENGTH + 4) {
                return null
            }

            val cryptoHash = ByteArray(CONTENT_HASH_LENGTH)
            recordBuf.get(cryptoHash)

            val uncompressedSize = recordBuf.int  // Now reads as little-endian
            val isCompressed = uncompressedSize < 0
            val actualSize = if (isCompressed) -uncompressedSize else uncompressedSize

            val compressedData = ByteArray(recordBuf.remaining())
            recordBuf.get(compressedData)

            val content = if (isCompressed && compressedData.isNotEmpty()) {
                decompress(compressedData, actualSize)
            } else {
                compressedData
            }

            return ContentRecord(contentId, cryptoHash, isCompressed, actualSize, content)
        } catch (e: Exception) {
            return null
        }
    }

    override fun listContentIds(): List<Int> {
        val ids = mutableListOf<Int>()
        var offset = AOL_HEADER_SIZE.toLong()

        while (offset < fileSize - 4) {
            try {
                val headerBuf = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN)
                val bytesRead = channel.read(headerBuf, offset)
                if (bytesRead < 4) break

                headerBuf.flip()
                val lengthField = headerBuf.int

                // Check for null/deleted record (all zeros = unwritten)
                if (lengthField == 0) {
                    break  // End of written data
                }

                val recordLength = lengthField and 0x3FFFFFFF

                if (recordLength <= 0 || recordLength > 100_000_000) {
                    break  // Invalid record, stop iteration
                }

                // Check record type: bit 31 = 0 means data record, 1 means padding
                val isPadding = (lengthField and (1 shl 31)) != 0

                // Only add data records (not padding) that have valid content
                if (!isPadding && recordLength >= CONTENT_HASH_LENGTH + 4) {
                    // Convert offset to recordId
                    ids.add(offsetToRecordId(offset))
                }

                // Move to next record: round up (offset + recordLength) to 4-byte alignment
                val nextOffset = roundUpToInt32(offset + recordLength)
                offset = nextOffset
            } catch (e: Exception) {
                break
            }
        }

        return ids
    }

    // Conversion functions matching IntelliJ's AppendOnlyLogOverMMappedFile
    private fun recordIdToOffset(recordId: Int): Long {
        // offset = ((recordId - 1) << 2) + HEADER_SIZE
        return ((recordId.toLong() - 1) shl 2) + AOL_HEADER_SIZE
    }

    private fun offsetToRecordId(offset: Long): Int {
        // recordId = ((offset - HEADER_SIZE) >> 2) + 1
        return (((offset - AOL_HEADER_SIZE) shr 2) + 1).toInt()
    }

    private fun roundUpToInt32(value: Long): Long {
        // Round up to next 4-byte boundary
        return (value + 3) and 0xFFFFFFFC.toLong()
    }

    override fun getRecordCount(): Int {
        return listContentIds().size
    }

    override fun close() {
        channel.close()
    }

    private fun decompress(compressed: ByteArray, expectedSize: Int): ByteArray {
        if (compressed.isEmpty()) return ByteArray(0)

        // Try LZ4 first (used by IntelliJ for compression)
        try {
            val decompressor = lz4Factory.fastDecompressor()
            val output = ByteArray(expectedSize)
            decompressor.decompress(compressed, 0, output, 0, expectedSize)
            return output
        } catch (e: Exception) {
            // Fall through to try Deflate
        }

        // Try Deflate (java.util.zip)
        try {
            val inflater = Inflater()
            inflater.setInput(compressed)
            val output = ByteArray(expectedSize)
            val actualSize = inflater.inflate(output)
            inflater.end()
            return if (actualSize == expectedSize) output else output.copyOf(actualSize)
        } catch (e: Exception) {
            // Return compressed data if decompression fails
            return compressed
        }
    }
}

/**
 * Reader for legacy AbstractStorage format (IntelliJ 2023.x and earlier)
 */
class LegacyContentReader(
    private val indexPath: Path,
    dataPath: Path
) : ContentStorageReader(dataPath) {

    private val indexChannel: FileChannel = FileChannel.open(indexPath, StandardOpenOption.READ)
    private val dataChannel: FileChannel = FileChannel.open(dataPath, StandardOpenOption.READ)
    private val lz4Factory = LZ4Factory.fastestInstance()

    private val recordCount: Int
    private val headerMagic: Int
    private val headerVersion: Int

    init {
        val indexSize = indexPath.fileSize()
        recordCount = ((indexSize - LEGACY_HEADER_SIZE) / LEGACY_RECORD_SIZE).toInt()

        // Read and validate header
        val headerBuf = ByteBuffer.allocate(LEGACY_HEADER_SIZE).order(ByteOrder.BIG_ENDIAN)
        indexChannel.read(headerBuf, 0)
        headerBuf.flip()
        headerMagic = headerBuf.int
        headerVersion = headerBuf.int
    }

    override fun readContent(contentId: Int): ContentRecord? {
        if (contentId < 1 || contentId > recordCount) {
            return null
        }

        try {
            // Read record from index
            val recordOffset = LEGACY_HEADER_SIZE + (contentId - 1) * LEGACY_RECORD_SIZE
            val indexBuf = ByteBuffer.allocate(LEGACY_RECORD_SIZE).order(ByteOrder.BIG_ENDIAN)
            indexChannel.read(indexBuf, recordOffset.toLong())
            indexBuf.flip()

            val address = indexBuf.long
            val size = indexBuf.int

            if (address <= 0 || size <= 0) {
                return null
            }

            // Read content from data file
            val dataBuf = ByteBuffer.allocate(size).order(ByteOrder.BIG_ENDIAN)
            dataChannel.read(dataBuf, address)
            dataBuf.flip()

            // Parse record: cryptoHash[20] + uncompressedSize(int32) + content[...]
            if (size < CONTENT_HASH_LENGTH + 4) {
                return null
            }

            val cryptoHash = ByteArray(CONTENT_HASH_LENGTH)
            dataBuf.get(cryptoHash)

            val uncompressedSize = dataBuf.int
            val isCompressed = uncompressedSize < 0
            val actualSize = if (isCompressed) -uncompressedSize else uncompressedSize

            val compressedData = ByteArray(dataBuf.remaining())
            dataBuf.get(compressedData)

            val content = if (isCompressed && compressedData.isNotEmpty()) {
                decompress(compressedData, actualSize)
            } else {
                compressedData
            }

            return ContentRecord(contentId, cryptoHash, isCompressed, actualSize, content)
        } catch (e: Exception) {
            return null
        }
    }

    override fun listContentIds(): List<Int> {
        val ids = mutableListOf<Int>()

        for (i in 1..recordCount) {
            val recordOffset = LEGACY_HEADER_SIZE + (i - 1) * LEGACY_RECORD_SIZE
            val indexBuf = ByteBuffer.allocate(LEGACY_RECORD_SIZE).order(ByteOrder.BIG_ENDIAN)
            indexChannel.read(indexBuf, recordOffset.toLong())
            indexBuf.flip()

            val address = indexBuf.long
            val size = indexBuf.int

            if (address > 0 && size > 0) {
                ids.add(i)
            }
        }

        return ids
    }

    override fun getRecordCount(): Int = recordCount

    override fun close() {
        indexChannel.close()
        dataChannel.close()
    }

    private fun decompress(compressed: ByteArray, expectedSize: Int): ByteArray {
        if (compressed.isEmpty()) return ByteArray(0)

        // Try LZ4 first
        try {
            val decompressor = lz4Factory.fastDecompressor()
            val output = ByteArray(expectedSize)
            decompressor.decompress(compressed, 0, output, 0, expectedSize)
            return output
        } catch (e: Exception) {
            // Fall through to try Deflate
        }

        // Try Deflate
        try {
            val inflater = Inflater()
            inflater.setInput(compressed)
            val output = ByteArray(expectedSize)
            val actualSize = inflater.inflate(output)
            inflater.end()
            return if (actualSize == expectedSize) output else output.copyOf(actualSize)
        } catch (e: Exception) {
            return compressed
        }
    }
}

/**
 * Get the default IntelliJ caches directory
 */
fun getDefaultCachesDir(): Path {
    val home = System.getProperty("user.home")
    val cacheDir = Path.of(home, "Library/Caches/JetBrains")

    // Find the most recent IntelliJ version
    val ideaDirs = cacheDir.toFile().listFiles { file ->
        file.isDirectory && file.name.startsWith("IntelliJIdea")
    }?.sortedByDescending { it.lastModified() }

    return ideaDirs?.firstOrNull()?.let {
        Path.of(it.absolutePath, "caches")
    } ?: Path.of(home, "Library/Caches/JetBrains/IntelliJIdea2025.2/caches")
}
