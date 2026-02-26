package com.stapler.localhistory.model

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * Unified domain models for LocalHistory data.
 *
 * This package provides a single source of truth for all LocalHistory-related
 * data structures, eliminating duplication across the codebase.
 */

/**
 * Types of changes tracked in LocalHistory.
 */
enum class ChangeType {
    CREATE_FILE,
    CREATE_DIRECTORY,
    CONTENT_CHANGE,
    RENAME,
    RO_STATUS_CHANGE,
    MOVE,
    DELETE,
    PUT_LABEL,
    PUT_SYSTEM_LABEL,
    UNKNOWN;

    companion object {
        /**
         * Convert from IntelliJ's numeric change type ID.
         */
        fun fromId(id: Int): ChangeType = when (id) {
            1 -> CREATE_FILE
            2 -> CREATE_DIRECTORY
            3 -> CONTENT_CHANGE
            4 -> RENAME
            5 -> RO_STATUS_CHANGE
            6 -> MOVE
            7 -> DELETE
            8 -> PUT_LABEL
            9 -> PUT_SYSTEM_LABEL
            else -> UNKNOWN
        }

        /**
         * Convert from IntelliJ's string change type name.
         */
        fun fromName(name: String): ChangeType = when (name) {
            "CreateFile" -> CREATE_FILE
            "CreateDirectory" -> CREATE_DIRECTORY
            "ContentChange" -> CONTENT_CHANGE
            "Rename" -> RENAME
            "ROStatusChange" -> RO_STATUS_CHANGE
            "Move" -> MOVE
            "Delete" -> DELETE
            "PutLabel" -> PUT_LABEL
            "PutSystemLabel" -> PUT_SYSTEM_LABEL
            else -> UNKNOWN
        }

        /**
         * Get the string name for a change type (for display/serialization).
         */
        fun toName(type: ChangeType): String = when (type) {
            CREATE_FILE -> "CreateFile"
            CREATE_DIRECTORY -> "CreateDirectory"
            CONTENT_CHANGE -> "ContentChange"
            RENAME -> "Rename"
            RO_STATUS_CHANGE -> "ROStatusChange"
            MOVE -> "Move"
            DELETE -> "Delete"
            PUT_LABEL -> "PutLabel"
            PUT_SYSTEM_LABEL -> "PutSystemLabel"
            UNKNOWN -> "Unknown"
        }
    }
}

/**
 * Represents a single change event in LocalHistory.
 */
data class Change(
    val type: ChangeType,
    val path: String?,
    val contentId: Int?,
    val oldPath: String? = null,  // For renames/moves
    val timestamp: Long? = null
) {
    val hasContent: Boolean get() = contentId != null && contentId > 0

    /**
     * Get the change type as a display string.
     */
    val typeString: String get() = ChangeType.toName(type)
}

/**
 * Represents a group of related changes at a point in time.
 */
data class ChangeSet(
    val id: Long,
    val name: String?,
    val timestamp: Long,
    val changes: List<Change>,
    val activityId: String? = null,
    val activityProvider: String? = null
) {
    val timestampInstant: Instant get() = Instant.ofEpochMilli(timestamp)

    val timestampStr: String
        get() = if (timestamp > 0) {
            Instant.ofEpochMilli(timestamp)
                .atZone(ZoneId.systemDefault())
                .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
        } else "N/A"

    val affectedPaths: List<String> get() = changes.mapNotNull { it.path }

    val hasContentChanges: Boolean get() = changes.any { it.type == ChangeType.CONTENT_CHANGE }

    val hasDeletions: Boolean get() = changes.any { it.type == ChangeType.DELETE }
}

/**
 * Represents a record from the index file (low-level storage metadata).
 */
data class IndexRecord(
    val id: Int,
    val address: Long,
    val size: Int,
    val capacity: Int,
    val prevRecord: Int,
    val nextRecord: Int,
    val timestamp: Long
) {
    val timestampStr: String
        get() = if (timestamp > 0) {
            Instant.ofEpochMilli(timestamp)
                .atZone(ZoneId.systemDefault())
                .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
        } else "N/A"
}

/**
 * Content record from the storage.
 */
data class ContentRecord(
    val contentId: Int,
    val hash: String,
    val content: ByteArray,
    val isCompressed: Boolean = false,
    val uncompressedSize: Int = content.size
) {
    /**
     * Check if content appears to be text (heuristic based on printable characters).
     */
    fun isText(): Boolean {
        if (content.isEmpty()) return true
        val sample = content.take(1024)
        var printable = 0
        for (b in sample) {
            val i = b.toInt() and 0xFF
            if (i in 0x20..0x7E || i == 0x09 || i == 0x0A || i == 0x0D) {
                printable++
            }
        }
        return printable.toDouble() / sample.size > 0.85
    }

    fun contentAsString(): String = String(content, Charsets.UTF_8)

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is ContentRecord) return false
        return contentId == other.contentId && hash == other.hash
    }

    override fun hashCode(): Int = contentId * 31 + hash.hashCode()
}

/**
 * Filter options for querying change sets.
 */
data class ChangeFilter(
    val limit: Int = Int.MAX_VALUE,
    val afterTimestamp: Long? = null,
    val beforeTimestamp: Long? = null,
    val pathContains: String? = null,
    val changeTypes: Set<ChangeType>? = null,
    val projectPath: String? = null
)

/**
 * Statistics about LocalHistory storage.
 */
data class LocalHistoryStats(
    val totalChangeSets: Int,
    val totalChanges: Int,
    val totalContentRecords: Int,
    val oldestTimestamp: Long?,
    val newestTimestamp: Long?,
    val totalContentSizeBytes: Long,
    val storageFormat: String
)

// Type aliases for backward compatibility
@Deprecated("Use model.ChangeType instead", ReplaceWith("com.stapler.localhistory.model.ChangeType"))
typealias LegacyChangeType = ChangeType
