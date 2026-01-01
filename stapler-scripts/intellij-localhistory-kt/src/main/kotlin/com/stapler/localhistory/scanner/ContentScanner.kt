package com.stapler.localhistory.scanner

import com.stapler.localhistory.ContentRecord
import com.stapler.localhistory.ContentStorageReader
import java.nio.charset.Charset
import java.nio.charset.StandardCharsets
import kotlin.math.min

/**
 * Configuration for content scanning operations
 */
data class ScanConfig(
    val maxRecords: Int = Int.MAX_VALUE,
    val skipCorrupted: Boolean = true,
    val textOnly: Boolean = false,
    val minSize: Int = 0,
    val maxSize: Int = Int.MAX_VALUE
)

/**
 * Metadata about a content record
 */
data class ContentMetadata(
    val contentId: Int,
    val hash: String,
    val size: Int,
    val isCompressed: Boolean,
    val isText: Boolean
)

/**
 * Result of scanning a content record
 */
data class ContentScanResult(
    val metadata: ContentMetadata,
    val preview: String?,
    val fileType: String?,
    val content: ByteArray? = null  // Only populated on demand
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is ContentScanResult) return false

        if (metadata != other.metadata) return false
        if (preview != other.preview) return false
        if (fileType != other.fileType) return false
        if (content != null) {
            if (other.content == null) return false
            if (!content.contentEquals(other.content)) return false
        } else if (other.content != null) return false

        return true
    }

    override fun hashCode(): Int {
        var result = metadata.hashCode()
        result = 31 * result + (preview?.hashCode() ?: 0)
        result = 31 * result + (fileType?.hashCode() ?: 0)
        result = 31 * result + (content?.contentHashCode() ?: 0)
        return result
    }
}

/**
 * Scanner for efficiently traversing content records
 *
 * Provides memory-efficient streaming through content records with progress
 * tracking and error recovery capabilities.
 */
class ContentScanner(private val contentReader: ContentStorageReader) {

    companion object {
        private const val PREVIEW_MAX_LENGTH = 500
        private const val PREVIEW_LINES = 10

        // File type detection based on content patterns
        private val FILE_TYPE_PATTERNS = mapOf(
            "xml" to "<?xml".toByteArray(),
            "html" to "<!DOCTYPE html".toByteArray(),
            "html" to "<html".toByteArray(),
            "json" to listOf("{", "[").map { it.toByteArray() },
            "java" to listOf("package ", "import ", "public class").map { it.toByteArray() },
            "kotlin" to listOf("package ", "import ", "fun ", "class ", "interface ").map { it.toByteArray() },
            "python" to listOf("import ", "from ", "def ", "class ").map { it.toByteArray() },
            "javascript" to listOf("function ", "const ", "let ", "var ", "import ").map { it.toByteArray() },
            "typescript" to listOf("interface ", "type ", "export ", "import ").map { it.toByteArray() },
            "css" to listOf(".", "#", "body", "html", "@media").map { it.toByteArray() },
            "sql" to listOf("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE").map { it.toByteArray() },
            "markdown" to listOf("# ", "## ", "- ", "* ", "[").map { it.toByteArray() },
            "yaml" to listOf("---", "- ", ":").map { it.toByteArray() },
            "properties" to "=".toByteArray(),
            "gradle" to listOf("dependencies", "plugins", "repositories").map { it.toByteArray() },
            "maven" to "<project".toByteArray()
        )
    }

    /**
     * Scan content with specified configuration and optional progress callback
     *
     * @param config Configuration for the scan
     * @param onProgress Optional callback for progress updates (current, total)
     * @return Lazy sequence of scan results
     */
    fun scan(
        config: ScanConfig = ScanConfig(),
        onProgress: ((Int, Int) -> Unit)? = null
    ): Sequence<ContentScanResult> {
        val contentIds = contentReader.listContentIds()
        val totalRecords = minOf(contentIds.size, config.maxRecords)

        return sequence {
            var processedCount = 0

            for (contentId in contentIds) {
                if (processedCount >= config.maxRecords) {
                    break
                }

                try {
                    val record = contentReader.readContent(contentId)

                    if (record != null) {
                        val scanResult = processRecord(record, config)

                        if (scanResult != null) {
                            yield(scanResult)
                        }
                    }
                } catch (e: Exception) {
                    if (!config.skipCorrupted) {
                        throw e
                    }
                    // Skip corrupted record: Failed to read content ID $contentId: ${e.message}
                }

                processedCount++
                onProgress?.invoke(processedCount, totalRecords)
            }
        }
    }

    /**
     * Scan content matching a regex pattern
     *
     * @param pattern Regex pattern to match content against
     * @param config Configuration for the scan
     * @return Lazy sequence of scan results matching the pattern
     */
    fun scanByPattern(
        pattern: Regex,
        config: ScanConfig = ScanConfig()
    ): Sequence<ContentScanResult> {
        return scan(config).filter { result ->
            try {
                // Check preview first (most efficient)
                if (result.preview?.contains(pattern) == true) {
                    return@filter true
                }

                // If no match in preview, check full content if text
                if (result.metadata.isText) {
                    val fullContent = getContent(result.metadata.contentId)
                    if (fullContent != null) {
                        val text = String(fullContent, StandardCharsets.UTF_8)
                        return@filter pattern.containsMatchIn(text)
                    }
                }

                false
            } catch (e: Exception) {
                // Pattern matching failed for content ${result.metadata.contentId}: ${e.message}
                false
            }
        }
    }

    /**
     * Get full content for a specific content ID
     *
     * @param contentId The ID of the content to retrieve
     * @return Content bytes or null if not found
     */
    fun getContent(contentId: Int): ByteArray? {
        return try {
            contentReader.readContent(contentId)?.content
        } catch (e: Exception) {
            println("Error: Failed to read content ID $contentId: ${e.message}")
            null
        }
    }

    /**
     * Process a single content record into a scan result
     */
    private fun processRecord(
        record: ContentRecord,
        config: ScanConfig
    ): ContentScanResult? {
        // Apply size filters
        val contentSize = record.content.size
        if (contentSize < config.minSize || contentSize > config.maxSize) {
            return null
        }

        // Determine if content is text
        val isText = isTextContent(record.content)

        // Apply text-only filter if configured
        if (config.textOnly && !isText) {
            return null
        }

        // Create metadata
        val metadata = ContentMetadata(
            contentId = record.contentId,
            hash = record.cryptoHashHex,
            size = record.uncompressedSize,
            isCompressed = record.isCompressed,
            isText = isText
        )

        // Generate preview for text content
        val preview = if (isText) {
            generatePreview(record.content)
        } else {
            null
        }

        // Detect file type
        val fileType = detectFileType(record.content, isText)

        return ContentScanResult(
            metadata = metadata,
            preview = preview,
            fileType = fileType,
            content = null  // Don't store content by default for memory efficiency
        )
    }

    /**
     * Check if content appears to be text
     */
    private fun isTextContent(content: ByteArray): Boolean {
        if (content.isEmpty()) return true

        // Sample the first 1KB for efficiency
        val sampleSize = min(1024, content.size)
        var printableCount = 0
        var controlCount = 0

        for (i in 0 until sampleSize) {
            val b = content[i].toInt() and 0xFF
            when {
                b in 0x20..0x7E -> printableCount++  // Printable ASCII
                b == 0x09 || b == 0x0A || b == 0x0D -> printableCount++  // Tab, LF, CR
                b < 0x20 && b != 0x09 && b != 0x0A && b != 0x0D -> controlCount++  // Control chars
                b >= 0x80 -> {
                    // Could be UTF-8, check if valid UTF-8 sequence
                    if (isValidUtf8Byte(content, i)) {
                        printableCount++
                    } else {
                        controlCount++
                    }
                }
            }
        }

        val total = printableCount + controlCount
        return if (total == 0) true else (printableCount.toDouble() / total) > 0.85
    }

    /**
     * Check if byte at position is part of valid UTF-8 sequence
     */
    private fun isValidUtf8Byte(content: ByteArray, position: Int): Boolean {
        if (position >= content.size) return false

        val b = content[position].toInt() and 0xFF

        return when {
            b and 0x80 == 0 -> true  // ASCII
            b and 0xE0 == 0xC0 -> {  // 2-byte sequence
                position + 1 < content.size &&
                (content[position + 1].toInt() and 0xC0) == 0x80
            }
            b and 0xF0 == 0xE0 -> {  // 3-byte sequence
                position + 2 < content.size &&
                (content[position + 1].toInt() and 0xC0) == 0x80 &&
                (content[position + 2].toInt() and 0xC0) == 0x80
            }
            b and 0xF8 == 0xF0 -> {  // 4-byte sequence
                position + 3 < content.size &&
                (content[position + 1].toInt() and 0xC0) == 0x80 &&
                (content[position + 2].toInt() and 0xC0) == 0x80 &&
                (content[position + 3].toInt() and 0xC0) == 0x80
            }
            else -> false
        }
    }

    /**
     * Generate a text preview from content
     */
    private fun generatePreview(content: ByteArray): String? {
        return try {
            val text = String(content, StandardCharsets.UTF_8)
            val lines = text.lines()

            // Take first N lines or max length, whichever comes first
            val previewLines = lines.take(PREVIEW_LINES)
            val preview = previewLines.joinToString("\n")

            if (preview.length > PREVIEW_MAX_LENGTH) {
                preview.substring(0, PREVIEW_MAX_LENGTH) + "..."
            } else if (lines.size > PREVIEW_LINES) {
                "$preview\n..."
            } else {
                preview
            }
        } catch (e: Exception) {
            // Failed to generate preview: ${e.message}
            null
        }
    }

    /**
     * Attempt to detect file type from content
     */
    private fun detectFileType(content: ByteArray, isText: Boolean): String? {
        if (!isText || content.isEmpty()) {
            return null
        }

        // Check magic bytes and patterns
        for ((fileType, patterns) in FILE_TYPE_PATTERNS) {
            when (patterns) {
                is ByteArray -> {
                    if (content.startsWith(patterns)) {
                        return fileType
                    }
                }
                is List<*> -> {
                    @Suppress("UNCHECKED_CAST")
                    for (pattern in patterns as List<ByteArray>) {
                        if (containsPattern(content, pattern, 200)) {  // Check first 200 bytes
                            return fileType
                        }
                    }
                }
            }
        }

        return if (isText) "text" else null
    }

    /**
     * Check if content starts with specific bytes
     */
    private fun ByteArray.startsWith(prefix: ByteArray): Boolean {
        if (this.size < prefix.size) return false
        for (i in prefix.indices) {
            if (this[i] != prefix[i]) return false
        }
        return true
    }

    /**
     * Check if pattern exists within first maxBytes of content
     */
    private fun containsPattern(content: ByteArray, pattern: ByteArray, maxBytes: Int): Boolean {
        val searchLimit = min(maxBytes, content.size - pattern.size + 1)
        if (searchLimit <= 0) return false

        for (i in 0 until searchLimit) {
            var match = true
            for (j in pattern.indices) {
                if (content[i + j] != pattern[j]) {
                    match = false
                    break
                }
            }
            if (match) return true
        }
        return false
    }
}