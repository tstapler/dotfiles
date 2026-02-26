package com.stapler.localhistory.cache

import com.stapler.localhistory.ContentStorageReader
import com.stapler.localhistory.analyzer.ContentClassifier
import com.stapler.localhistory.scanner.ContentMetadata
import com.stapler.localhistory.scanner.ContentScanResult
import java.io.*
import java.nio.file.Path
import java.security.MessageDigest
import java.util.concurrent.ConcurrentHashMap
import kotlin.io.path.exists
import kotlin.io.path.getLastModifiedTime

/**
 * Cache entry for content metadata
 */
data class CacheEntry(
    val contentId: Int,
    val hash: String,
    val size: Int,
    val isCompressed: Boolean,
    val isText: Boolean,
    val fileType: String?,
    val simHash: String?,
    val preview: String?,
    val cachedAt: Long = System.currentTimeMillis()
) : Serializable {
    companion object {
        private const val serialVersionUID = 1L
    }

    fun toScanResult(): ContentScanResult {
        return ContentScanResult(
            metadata = ContentMetadata(
                contentId = contentId,
                hash = hash,
                size = size,
                isCompressed = isCompressed,
                isText = isText
            ),
            preview = preview,
            fileType = fileType
        )
    }

    fun isExpired(maxAgeMs: Long): Boolean {
        return System.currentTimeMillis() - cachedAt > maxAgeMs
    }
}

/**
 * Cache metadata stored in cache file header
 */
data class CacheMetadata(
    val version: Int = CACHE_VERSION,
    val createdAt: Long = System.currentTimeMillis(),
    val sourceStorageHash: String,  // Hash of content storage to detect changes
    val entryCount: Int
) : Serializable {
    companion object {
        private const val serialVersionUID = 1L
        const val CACHE_VERSION = 1
    }
}

/**
 * Persistent cache for content index data
 *
 * Provides fast access to content metadata without re-scanning the content storage.
 * Supports automatic invalidation when the underlying storage changes.
 */
class ContentIndexCache private constructor(
    private val cachePath: Path,
    private val contentStoragePath: Path
) {

    companion object {
        const val CACHE_VERSION = 1
        private const val DEFAULT_CACHE_FILE = "content-index.cache"
        private const val MAX_CACHE_AGE_MS = 24 * 60 * 60 * 1000L  // 24 hours
        private const val MAX_PREVIEW_LENGTH = 500

        /**
         * Create or load a cache for the given content storage
         */
        fun forStorage(
            contentStoragePath: Path,
            cacheDir: Path = contentStoragePath.parent.resolve(".localhistory-cache")
        ): ContentIndexCache {
            val cachePath = cacheDir.resolve(DEFAULT_CACHE_FILE)
            return ContentIndexCache(cachePath, contentStoragePath)
        }
    }

    // In-memory cache
    private val entries = ConcurrentHashMap<Int, CacheEntry>()
    private var metadata: CacheMetadata? = null
    private var dirty = false

    /**
     * Check if cache is valid (exists and matches current storage)
     */
    fun isValid(): Boolean {
        if (!cachePath.exists()) return false

        val currentHash = calculateStorageHash()
        return metadata?.sourceStorageHash == currentHash &&
               !isCacheExpired()
    }

    /**
     * Load cache from disk
     *
     * @return true if cache was loaded successfully
     */
    fun load(): Boolean {
        if (!cachePath.exists()) {
            return false
        }

        return try {
            ObjectInputStream(BufferedInputStream(FileInputStream(cachePath.toFile()))).use { ois ->
                @Suppress("UNCHECKED_CAST")
                metadata = ois.readObject() as CacheMetadata

                // Check if cache version matches
                if (metadata?.version != CACHE_VERSION) {
                    clear()
                    return false
                }

                // Check if storage has changed
                val currentHash = calculateStorageHash()
                if (metadata?.sourceStorageHash != currentHash) {
                    clear()
                    return false
                }

                // Load entries
                val entryCount = metadata?.entryCount ?: 0
                repeat(entryCount) {
                    val entry = ois.readObject() as CacheEntry
                    entries[entry.contentId] = entry
                }

                true
            }
        } catch (e: Exception) {
            println("Warning: Failed to load cache: ${e.message}")
            clear()
            false
        }
    }

    /**
     * Save cache to disk
     *
     * @return true if cache was saved successfully
     */
    fun save(): Boolean {
        if (!dirty && cachePath.exists()) {
            return true  // Nothing to save
        }

        return try {
            // Ensure cache directory exists
            cachePath.parent.toFile().mkdirs()

            val storageHash = calculateStorageHash()
            metadata = CacheMetadata(
                sourceStorageHash = storageHash,
                entryCount = entries.size
            )

            ObjectOutputStream(BufferedOutputStream(FileOutputStream(cachePath.toFile()))).use { oos ->
                oos.writeObject(metadata)
                for (entry in entries.values) {
                    oos.writeObject(entry)
                }
            }

            dirty = false
            true
        } catch (e: Exception) {
            println("Warning: Failed to save cache: ${e.message}")
            false
        }
    }

    /**
     * Clear cache
     */
    fun clear() {
        entries.clear()
        metadata = null
        dirty = true

        if (cachePath.exists()) {
            try {
                cachePath.toFile().delete()
            } catch (e: Exception) {
                // Ignore deletion errors
            }
        }
    }

    /**
     * Get cached entry for content ID
     */
    fun get(contentId: Int): CacheEntry? {
        return entries[contentId]
    }

    /**
     * Get all cached entries
     */
    fun getAll(): List<CacheEntry> {
        return entries.values.toList()
    }

    /**
     * Get all cached entries as scan results
     */
    fun getAllAsScanResults(): List<ContentScanResult> {
        return entries.values.map { it.toScanResult() }
    }

    /**
     * Put entry into cache
     */
    fun put(entry: CacheEntry) {
        entries[entry.contentId] = entry
        dirty = true
    }

    /**
     * Put multiple entries into cache
     */
    fun putAll(newEntries: List<CacheEntry>) {
        for (entry in newEntries) {
            entries[entry.contentId] = entry
        }
        dirty = true
    }

    /**
     * Check if content ID is cached
     */
    fun contains(contentId: Int): Boolean {
        return entries.containsKey(contentId)
    }

    /**
     * Get number of cached entries
     */
    fun size(): Int = entries.size

    /**
     * Build cache from content storage
     *
     * @param reader Content storage reader
     * @param classifier Content classifier for type detection
     * @param onProgress Optional progress callback
     * @return Number of entries cached
     */
    fun buildFromStorage(
        reader: ContentStorageReader,
        classifier: ContentClassifier = ContentClassifier(),
        onProgress: ((Int, Int) -> Unit)? = null
    ): Int {
        val contentIds = reader.listContentIds()
        val total = contentIds.size
        var processed = 0

        for (contentId in contentIds) {
            try {
                val record = reader.readContent(contentId)
                if (record != null) {
                    val isText = classifier.isTextContent(record.content)
                    val fileType = classifier.detectFileType(record.content)

                    val preview = if (isText) {
                        classifier.extractPreview(record.content, MAX_PREVIEW_LENGTH)
                    } else {
                        null
                    }

                    val simHash = if (isText) {
                        classifier.calculateSimHash(record.content)
                    } else {
                        null
                    }

                    val entry = CacheEntry(
                        contentId = record.contentId,
                        hash = record.cryptoHashHex,
                        size = record.uncompressedSize,
                        isCompressed = record.isCompressed,
                        isText = isText,
                        fileType = fileType?.extension,
                        simHash = simHash,
                        preview = preview
                    )

                    put(entry)
                }
            } catch (e: Exception) {
                // Skip entries that fail to read
            }

            processed++
            onProgress?.invoke(processed, total)
        }

        return entries.size
    }

    /**
     * Update cache incrementally (only add new entries)
     *
     * @param reader Content storage reader
     * @param classifier Content classifier
     * @return Number of new entries added
     */
    fun updateIncremental(
        reader: ContentStorageReader,
        classifier: ContentClassifier = ContentClassifier()
    ): Int {
        val contentIds = reader.listContentIds()
        var added = 0

        for (contentId in contentIds) {
            if (contains(contentId)) continue

            try {
                val record = reader.readContent(contentId)
                if (record != null) {
                    val isText = classifier.isTextContent(record.content)
                    val fileType = classifier.detectFileType(record.content)

                    val preview = if (isText) {
                        classifier.extractPreview(record.content, MAX_PREVIEW_LENGTH)
                    } else {
                        null
                    }

                    val simHash = if (isText) {
                        classifier.calculateSimHash(record.content)
                    } else {
                        null
                    }

                    val entry = CacheEntry(
                        contentId = record.contentId,
                        hash = record.cryptoHashHex,
                        size = record.uncompressedSize,
                        isCompressed = record.isCompressed,
                        isText = isText,
                        fileType = fileType?.extension,
                        simHash = simHash,
                        preview = preview
                    )

                    put(entry)
                    added++
                }
            } catch (e: Exception) {
                // Skip entries that fail
            }
        }

        return added
    }

    /**
     * Get statistics about the cache
     */
    fun getStats(): CacheStats {
        val textCount = entries.values.count { it.isText }
        val binaryCount = entries.size - textCount
        val totalSize = entries.values.sumOf { it.size.toLong() }
        val fileTypes = entries.values
            .groupingBy { it.fileType ?: "unknown" }
            .eachCount()

        return CacheStats(
            entryCount = entries.size,
            textCount = textCount,
            binaryCount = binaryCount,
            totalSizeBytes = totalSize,
            fileTypeDistribution = fileTypes,
            cacheCreatedAt = metadata?.createdAt,
            isValid = isValid()
        )
    }

    // Private helpers

    private fun calculateStorageHash(): String {
        return try {
            // Use storage file modification time and size as hash input
            val storageFile = contentStoragePath.toFile()
            if (!storageFile.exists()) return ""

            val md = MessageDigest.getInstance("MD5")
            val input = "${storageFile.length()}-${storageFile.lastModified()}"
            md.update(input.toByteArray())
            md.digest().joinToString("") { "%02x".format(it) }
        } catch (e: Exception) {
            ""
        }
    }

    private fun isCacheExpired(): Boolean {
        val createdAt = metadata?.createdAt ?: return true
        return System.currentTimeMillis() - createdAt > MAX_CACHE_AGE_MS
    }
}

/**
 * Cache statistics
 */
data class CacheStats(
    val entryCount: Int,
    val textCount: Int,
    val binaryCount: Int,
    val totalSizeBytes: Long,
    val fileTypeDistribution: Map<String, Int>,
    val cacheCreatedAt: Long?,
    val isValid: Boolean
) {
    fun print() {
        println("=== Cache Statistics ===")
        println("Total entries: $entryCount")
        println("Text content: $textCount")
        println("Binary content: $binaryCount")
        println("Total size: ${formatSize(totalSizeBytes)}")
        println("Valid: $isValid")

        if (cacheCreatedAt != null) {
            val age = System.currentTimeMillis() - cacheCreatedAt
            println("Age: ${formatDuration(age)}")
        }

        if (fileTypeDistribution.isNotEmpty()) {
            println("\nTop file types:")
            fileTypeDistribution.entries
                .sortedByDescending { it.value }
                .take(5)
                .forEach { (type, count) ->
                    println("  $type: $count")
                }
        }
    }

    private fun formatSize(bytes: Long): String {
        return when {
            bytes < 1024 -> "$bytes B"
            bytes < 1024 * 1024 -> "${bytes / 1024} KB"
            bytes < 1024 * 1024 * 1024 -> "${bytes / (1024 * 1024)} MB"
            else -> "${bytes / (1024 * 1024 * 1024)} GB"
        }
    }

    private fun formatDuration(ms: Long): String {
        val seconds = ms / 1000
        val minutes = seconds / 60
        val hours = minutes / 60
        val days = hours / 24

        return when {
            days > 0 -> "$days days"
            hours > 0 -> "$hours hours"
            minutes > 0 -> "$minutes minutes"
            else -> "$seconds seconds"
        }
    }
}
