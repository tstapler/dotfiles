package com.stapler.localhistory.analyzer

import java.nio.charset.Charset
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import kotlin.math.min

/**
 * Represents the type of content in a file
 */
sealed class ContentType {
    object Text : ContentType()
    object Binary : ContentType()
    data class Structured(val format: String) : ContentType()
}

/**
 * File type information including extension, MIME type, and category
 */
data class FileTypeInfo(
    val extension: String,
    val mimeType: String,
    val category: String  // "source", "config", "document", "image", etc.
)

/**
 * Classifies file content, detects file types, and provides content analysis utilities
 */
class ContentClassifier {

    companion object {
        // Magic bytes for common file formats
        private val FILE_SIGNATURES = mapOf(
            // Documents
            byteArrayOf(0x25, 0x50, 0x44, 0x46) to FileTypeInfo("pdf", "application/pdf", "document"), // %PDF

            // Archives
            byteArrayOf(0x50, 0x4B, 0x03, 0x04) to FileTypeInfo("zip", "application/zip", "archive"), // PK\x03\x04
            byteArrayOf(0x50, 0x4B, 0x05, 0x06) to FileTypeInfo("zip", "application/zip", "archive"), // PK\x05\x06 (empty)
            byteArrayOf(0x50, 0x4B, 0x07, 0x08) to FileTypeInfo("zip", "application/zip", "archive"), // PK\x07\x08 (spanned)

            // Images
            byteArrayOf(0x89.toByte(), 0x50, 0x4E, 0x47) to FileTypeInfo("png", "image/png", "image"), // \x89PNG
            byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte()) to FileTypeInfo("jpg", "image/jpeg", "image"), // JPEG
            byteArrayOf(0x47, 0x49, 0x46, 0x38, 0x37, 0x61) to FileTypeInfo("gif", "image/gif", "image"), // GIF87a
            byteArrayOf(0x47, 0x49, 0x46, 0x38, 0x39, 0x61) to FileTypeInfo("gif", "image/gif", "image"), // GIF89a

            // Audio/Video
            byteArrayOf(0x49, 0x44, 0x33) to FileTypeInfo("mp3", "audio/mpeg", "audio"), // ID3
            byteArrayOf(0xFF.toByte(), 0xFB.toByte()) to FileTypeInfo("mp3", "audio/mpeg", "audio"), // MP3

            // Executables
            byteArrayOf(0x4D, 0x5A) to FileTypeInfo("exe", "application/x-msdownload", "executable"), // MZ
            byteArrayOf(0x7F, 0x45, 0x4C, 0x46) to FileTypeInfo("elf", "application/x-elf", "executable"), // ELF
            byteArrayOf(0xCA.toByte(), 0xFE.toByte(), 0xBA.toByte(), 0xBE.toByte()) to
                FileTypeInfo("class", "application/java-vm", "bytecode"), // Java class
            byteArrayOf(0xCE.toByte(), 0xFA.toByte(), 0xED.toByte(), 0xFE.toByte()) to
                FileTypeInfo("mach-o", "application/x-mach-binary", "executable"), // Mach-O
        )

        // Text-based format patterns
        private val TEXT_PATTERNS = mapOf(
            "<?xml" to FileTypeInfo("xml", "application/xml", "config"),
            "<!DOCTYPE" to FileTypeInfo("html", "text/html", "document"),
            "<html" to FileTypeInfo("html", "text/html", "document"),
        )

        // Source code patterns (first non-whitespace content)
        private val SOURCE_PATTERNS = mapOf(
            Regex("^\\s*package\\s+") to FileTypeInfo("java", "text/x-java-source", "source"),
            Regex("^\\s*import\\s+java") to FileTypeInfo("java", "text/x-java-source", "source"),
            Regex("^\\s*public\\s+class\\s+") to FileTypeInfo("java", "text/x-java-source", "source"),
            Regex("^\\s*public\\s+interface\\s+") to FileTypeInfo("java", "text/x-java-source", "source"),
            Regex("^\\s*fun\\s+") to FileTypeInfo("kt", "text/x-kotlin", "source"),
            Regex("^\\s*class\\s+\\w+\\s*\\(") to FileTypeInfo("kt", "text/x-kotlin", "source"),
            Regex("^\\s*interface\\s+\\w+\\s*\\{") to FileTypeInfo("kt", "text/x-kotlin", "source"),
            Regex("^\\s*import\\s+['\"]") to FileTypeInfo("js", "text/javascript", "source"),
            Regex("^\\s*export\\s+(default|const|function|class)") to FileTypeInfo("js", "text/javascript", "source"),
            Regex("^\\s*const\\s+\\w+\\s*=") to FileTypeInfo("js", "text/javascript", "source"),
            Regex("^\\s*function\\s+\\w+\\s*\\(") to FileTypeInfo("js", "text/javascript", "source"),
            Regex("^\\s*SELECT\\s+", RegexOption.IGNORE_CASE) to FileTypeInfo("sql", "text/x-sql", "source"),
            Regex("^\\s*INSERT\\s+INTO", RegexOption.IGNORE_CASE) to FileTypeInfo("sql", "text/x-sql", "source"),
            Regex("^\\s*CREATE\\s+(TABLE|DATABASE|INDEX)", RegexOption.IGNORE_CASE) to FileTypeInfo("sql", "text/x-sql", "source"),
            Regex("^\\s*ALTER\\s+TABLE", RegexOption.IGNORE_CASE) to FileTypeInfo("sql", "text/x-sql", "source"),
            Regex("^#!/usr/bin/(env\\s+)?(python|python3)") to FileTypeInfo("py", "text/x-python", "source"),
            Regex("^\\s*def\\s+\\w+\\s*\\(") to FileTypeInfo("py", "text/x-python", "source"),
            Regex("^\\s*class\\s+\\w+\\s*:") to FileTypeInfo("py", "text/x-python", "source"),
            Regex("^\\s*import\\s+\\w+") to FileTypeInfo("py", "text/x-python", "source"),
            Regex("^\\s*from\\s+\\w+\\s+import") to FileTypeInfo("py", "text/x-python", "source"),
        )

        // Structured format detection
        private val STRUCTURED_PATTERNS = mapOf(
            Regex("^\\s*\\{.*\".*\":") to "JSON",
            Regex("^\\s*\\[\\s*\\{") to "JSON",
            Regex("^\\s*---\\s*\n") to "YAML",
            Regex("^\\s*\\w+:\\s*\n\\s+") to "YAML",
            Regex("^\\s*<\\?xml") to "XML",
            Regex("^\\s*<\\w+[^>]*>") to "XML",
            Regex("^\\s*#\\s+\\w+") to "Markdown",
            Regex("^\\s*##\\s+\\w+") to "Markdown",
        )

        private const val MAX_PATTERN_CHECK_LENGTH = 1024
        private const val TEXT_THRESHOLD = 0.9
    }

    /**
     * Classifies content as Text, Binary, or Structured
     */
    fun classify(content: ByteArray): ContentType {
        // Check if it's binary first
        if (!isTextContent(content)) {
            return ContentType.Binary
        }

        // Check for structured formats
        val textContent = String(content.take(MAX_PATTERN_CHECK_LENGTH).toByteArray(), StandardCharsets.UTF_8)
        for ((pattern, format) in STRUCTURED_PATTERNS) {
            if (pattern.containsMatchIn(textContent)) {
                return ContentType.Structured(format)
            }
        }

        return ContentType.Text
    }

    /**
     * Detects file type from magic bytes and content patterns
     */
    fun detectFileType(content: ByteArray): FileTypeInfo? {
        if (content.isEmpty()) return null

        // Check magic bytes first
        for ((signature, fileType) in FILE_SIGNATURES) {
            if (content.size >= signature.size &&
                content.take(signature.size).toByteArray().contentEquals(signature)) {
                // Special case for JAR files (which are ZIP files)
                if (fileType.extension == "zip" && hasJarManifest(content)) {
                    return FileTypeInfo("jar", "application/java-archive", "archive")
                }
                return fileType
            }
        }

        // If it looks like text, check text patterns
        if (isTextContent(content)) {
            val textContent = String(content.take(MAX_PATTERN_CHECK_LENGTH).toByteArray(), StandardCharsets.UTF_8)

            // Check simple text patterns
            for ((pattern, fileType) in TEXT_PATTERNS) {
                if (textContent.startsWith(pattern, ignoreCase = true)) {
                    return fileType
                }
            }

            // Check source code patterns
            for ((pattern, fileType) in SOURCE_PATTERNS) {
                if (pattern.containsMatchIn(textContent)) {
                    return fileType
                }
            }
        }

        return null
    }

    /**
     * Extracts a text preview from content with smart truncation
     */
    fun extractPreview(content: ByteArray, maxLength: Int = 500): String? {
        if (!isTextContent(content)) {
            return null
        }

        return try {
            val text = String(content, StandardCharsets.UTF_8)
            when {
                text.length <= maxLength -> text
                else -> {
                    // Try to break at a natural boundary (end of line or sentence)
                    val truncated = text.take(maxLength)
                    val lastNewline = truncated.lastIndexOf('\n')
                    val lastPeriod = truncated.lastIndexOf('.')
                    val lastSpace = truncated.lastIndexOf(' ')

                    val breakPoint = maxOf(lastNewline, lastPeriod, lastSpace)
                    if (breakPoint > maxLength / 2) {
                        truncated.substring(0, breakPoint + 1).trim() + "..."
                    } else {
                        truncated.trim() + "..."
                    }
                }
            }
        } catch (e: Exception) {
            null
        }
    }

    /**
     * Determines if content is text-based (>90% printable ASCII or valid UTF-8)
     */
    fun isTextContent(content: ByteArray): Boolean {
        if (content.isEmpty()) return true

        // Check if it's valid UTF-8
        val text = try {
            String(content, StandardCharsets.UTF_8)
        } catch (e: Exception) {
            return false
        }

        // Count printable and control characters
        var printableCount = 0
        var totalCount = 0

        for (char in text.take(min(content.size, 8192))) { // Sample first 8KB
            totalCount++
            when {
                char.isLetterOrDigit() -> printableCount++
                char.isWhitespace() -> printableCount++
                char in '!'..'~' -> printableCount++ // ASCII printable range
                char == '\n' || char == '\r' || char == '\t' -> printableCount++
            }
        }

        // Calculate ratio of printable characters
        val ratio = if (totalCount > 0) printableCount.toDouble() / totalCount else 0.0
        return ratio >= TEXT_THRESHOLD
    }

    /**
     * Calculates a similarity hash for content grouping using SimHash algorithm
     */
    fun calculateSimHash(content: ByteArray): String {
        if (content.isEmpty()) return "0000000000000000"

        val text = if (isTextContent(content)) {
            String(content, StandardCharsets.UTF_8)
        } else {
            // For binary content, use hex representation of first 1KB
            content.take(1024).joinToString("") { "%02x".format(it) }
        }

        // Tokenize text into shingles (3-word sequences)
        val tokens = text.split(Regex("\\s+"))
            .filter { it.isNotBlank() }
            .windowed(3, 1, true)
            .map { it.joinToString(" ") }

        if (tokens.isEmpty()) {
            return calculateMD5Hash(content)
        }

        // Initialize feature vector
        val vectorSize = 64
        val vector = IntArray(vectorSize)

        // Calculate weighted feature vector
        for (token in tokens) {
            val hash = token.hashCode()
            for (i in 0 until vectorSize) {
                if ((hash and (1 shl i)) != 0) {
                    vector[i]++
                } else {
                    vector[i]--
                }
            }
        }

        // Generate final hash
        var simHash = 0L
        for (i in 0 until vectorSize) {
            if (vector[i] > 0) {
                simHash = simHash or (1L shl i)
            }
        }

        return "%016x".format(simHash)
    }

    /**
     * Calculates MD5 hash as fallback for similarity hashing
     */
    private fun calculateMD5Hash(content: ByteArray): String {
        val md = MessageDigest.getInstance("MD5")
        val digest = md.digest(content)
        return digest.take(8).joinToString("") { "%02x".format(it) }
    }

    /**
     * Checks if a ZIP file contains a JAR manifest
     */
    private fun hasJarManifest(content: ByteArray): Boolean {
        // Simple heuristic: look for "META-INF/MANIFEST.MF" in the content
        val searchString = "META-INF/MANIFEST.MF"
        val searchBytes = searchString.toByteArray()

        if (content.size < searchBytes.size) return false

        for (i in 0..content.size - searchBytes.size) {
            if (content.slice(i until i + searchBytes.size).toByteArray().contentEquals(searchBytes)) {
                return true
            }
        }
        return false
    }

    /**
     * Gets a human-readable description of the content type
     */
    fun getContentDescription(content: ByteArray): String {
        val contentType = classify(content)
        val fileType = detectFileType(content)

        return when (contentType) {
            is ContentType.Binary -> {
                fileType?.let { "Binary ${it.category}: ${it.mimeType}" } ?: "Binary file"
            }
            is ContentType.Structured -> {
                "${contentType.format} structured data"
            }
            is ContentType.Text -> {
                fileType?.let {
                    when (it.category) {
                        "source" -> "${it.extension.uppercase()} source code"
                        "config" -> "${it.extension.uppercase()} configuration"
                        "document" -> "${it.extension.uppercase()} document"
                        else -> "Text file (${it.mimeType})"
                    }
                } ?: "Plain text file"
            }
        }
    }

    /**
     * Analyzes content and returns comprehensive classification info
     */
    fun analyzeContent(content: ByteArray): ContentAnalysis {
        return ContentAnalysis(
            contentType = classify(content),
            fileTypeInfo = detectFileType(content),
            isText = isTextContent(content),
            preview = extractPreview(content),
            simHash = calculateSimHash(content),
            sizeBytes = content.size,
            description = getContentDescription(content)
        )
    }
}

/**
 * Comprehensive content analysis result
 */
data class ContentAnalysis(
    val contentType: ContentType,
    val fileTypeInfo: FileTypeInfo?,
    val isText: Boolean,
    val preview: String?,
    val simHash: String,
    val sizeBytes: Int,
    val description: String
)