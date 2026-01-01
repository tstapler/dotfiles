package com.stapler.localhistory.analyzer

import com.stapler.localhistory.*
import java.nio.file.Path
import java.time.Instant
import java.time.temporal.ChronoUnit
import kotlin.io.path.exists

/**
 * Represents the orphan status of content with confidence scoring
 */
sealed class OrphanStatus {
    /** Content is definitely still in use */
    object Active : OrphanStatus() {
        override fun toString() = "Active"
    }

    /** Content is definitely orphaned */
    object Orphaned : OrphanStatus() {
        override fun toString() = "Orphaned"
    }

    /** Content status is uncertain */
    data class Uncertain(val confidence: Float, val reason: String) : OrphanStatus() {
        override fun toString() = "Uncertain (confidence: ${confidence * 100}%, reason: $reason)"
    }
}

/**
 * Represents a reference to content from LocalHistory
 */
data class ContentReference(
    val contentId: Int,
    val path: String?,
    val timestamp: Long?,
    val changeType: String?  // "ContentChange", "Delete", etc.
) {
    val timestampInstant: Instant?
        get() = timestamp?.let { Instant.ofEpochMilli(it) }

    val isDeleteReference: Boolean
        get() = changeType == "Delete"

    val isContentChange: Boolean
        get() = changeType == "ContentChange"
}

/**
 * Detects orphaned content by analyzing references in LocalHistory
 */
open class OrphanDetector(
    private val localHistoryDir: Path,
    private val cachesDir: Path
) {

    companion object {
        // Confidence thresholds
        const val HIGH_CONFIDENCE = 0.9f
        const val MEDIUM_CONFIDENCE = 0.7f
        const val LOW_CONFIDENCE = 0.5f

        // Time thresholds
        const val RECENT_DAYS = 7L
        const val OLD_DAYS = 30L
        const val VERY_OLD_DAYS = 90L
    }

    /**
     * Build a map of content ID -> references from LocalHistory
     *
     * This method parses the LocalHistory storage and extracts all content references,
     * creating a comprehensive map of which content IDs are referenced and how.
     */
    open fun buildReferenceMap(): Map<Int, List<ContentReference>> {
        val referenceMap = mutableMapOf<Int, MutableList<ContentReference>>()

        val indexPath = localHistoryDir.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryDir.resolve("changes.storageData")

        if (!indexPath.exists() || !dataPath.exists()) {
            println("Warning: LocalHistory files not found in $localHistoryDir")
            return emptyMap()
        }

        try {
            val (_, records) = parseIndexFile(indexPath)
            val changeSets = parseDataFile(dataPath, records)

            // Process each change set to extract content references
            for (record in records) {
                val changeSet = changeSets[record.id] ?: continue

                for (change in changeSet.changes) {
                    change.contentId?.let { contentId ->
                        val reference = ContentReference(
                            contentId = contentId,
                            path = change.path,
                            timestamp = changeSet.timestamp,
                            changeType = change.changeType
                        )

                        referenceMap.computeIfAbsent(contentId) { mutableListOf() }
                            .add(reference)
                    }
                }
            }
        } catch (e: Exception) {
            println("Error building reference map: ${e.message}")
            e.printStackTrace()
        }

        return referenceMap
    }

    /**
     * Check if a specific content ID is orphaned
     *
     * Analyzes all references to determine orphan status with confidence scoring
     */
    fun checkOrphanStatus(
        contentId: Int,
        referenceMap: Map<Int, List<ContentReference>>
    ): OrphanStatus {
        val references = referenceMap[contentId]

        // No references at all - high confidence orphan
        if (references.isNullOrEmpty()) {
            return OrphanStatus.Uncertain(
                confidence = HIGH_CONFIDENCE,
                reason = "No references found in LocalHistory"
            )
        }

        // Analyze reference patterns
        val now = Instant.now()
        val sortedRefs = references.sortedByDescending { it.timestamp ?: 0 }
        val mostRecent = sortedRefs.firstOrNull()
        val hasDeleteReference = references.any { it.isDeleteReference }
        val hasContentChange = references.any { it.isContentChange }
        val deleteOnlyReferences = references.all { it.isDeleteReference }

        // Pattern 1: Only delete references - high confidence orphan
        if (deleteOnlyReferences) {
            return OrphanStatus.Orphaned
        }

        // Pattern 2: Has delete reference and no recent content changes
        if (hasDeleteReference) {
            val lastContentChange = references
                .filter { it.isContentChange }
                .maxByOrNull { it.timestamp ?: 0 }

            val lastDelete = references
                .filter { it.isDeleteReference }
                .maxByOrNull { it.timestamp ?: 0 }

            if (lastDelete != null &&
                (lastContentChange == null ||
                 (lastDelete.timestamp ?: 0) > (lastContentChange.timestamp ?: 0))) {
                return OrphanStatus.Orphaned
            }
        }

        // Pattern 3: Check recency of references
        mostRecent?.timestampInstant?.let { lastRefTime ->
            val daysSinceLastRef = ChronoUnit.DAYS.between(lastRefTime, now)

            // Very recent activity - definitely active
            if (daysSinceLastRef < RECENT_DAYS && hasContentChange) {
                return OrphanStatus.Active
            }

            // Recent activity - probably active
            if (daysSinceLastRef < RECENT_DAYS) {
                return OrphanStatus.Active
            }

            // Old but has content changes - uncertain
            if (daysSinceLastRef > OLD_DAYS && daysSinceLastRef < VERY_OLD_DAYS) {
                return OrphanStatus.Uncertain(
                    confidence = MEDIUM_CONFIDENCE,
                    reason = "No references for $daysSinceLastRef days"
                )
            }

            // Very old - high confidence orphan
            if (daysSinceLastRef > VERY_OLD_DAYS) {
                return OrphanStatus.Uncertain(
                    confidence = HIGH_CONFIDENCE,
                    reason = "No references for $daysSinceLastRef days (very old)"
                )
            }
        }

        // Pattern 4: Has content changes but no timestamp info
        if (hasContentChange && !hasDeleteReference) {
            return OrphanStatus.Active
        }

        // Default: uncertain with low confidence
        return OrphanStatus.Uncertain(
            confidence = LOW_CONFIDENCE,
            reason = "Mixed or unclear reference pattern"
        )
    }

    /**
     * Find all references for a specific content ID
     */
    fun findReferences(contentId: Int): List<ContentReference> {
        val references = mutableListOf<ContentReference>()

        val indexPath = localHistoryDir.resolve("changes.storageRecordIndex")
        val dataPath = localHistoryDir.resolve("changes.storageData")

        if (!indexPath.exists() || !dataPath.exists()) {
            return emptyList()
        }

        try {
            val (_, records) = parseIndexFile(indexPath)
            val changeSets = parseDataFile(dataPath, records)

            for (record in records) {
                val changeSet = changeSets[record.id] ?: continue

                for (change in changeSet.changes) {
                    if (change.contentId == contentId) {
                        references.add(ContentReference(
                            contentId = contentId,
                            path = change.path,
                            timestamp = changeSet.timestamp,
                            changeType = change.changeType
                        ))
                    }
                }
            }
        } catch (e: Exception) {
            println("Error finding references: ${e.message}")
        }

        return references.sortedByDescending { it.timestamp ?: 0 }
    }

    /**
     * Find all orphaned content with confidence scores
     *
     * @param contentIds List of content IDs to check
     * @param minConfidence Minimum confidence threshold for including in results
     * @return List of content IDs paired with their orphan status
     */
    fun findOrphanedContent(
        contentIds: List<Int>,
        minConfidence: Float = 0.7f
    ): List<Pair<Int, OrphanStatus>> {
        val referenceMap = buildReferenceMap()
        val orphanCandidates = mutableListOf<Pair<Int, OrphanStatus>>()

        for (contentId in contentIds) {
            val status = checkOrphanStatus(contentId, referenceMap)

            // Include based on status type and confidence
            when (status) {
                is OrphanStatus.Orphaned -> {
                    orphanCandidates.add(contentId to status)
                }
                is OrphanStatus.Uncertain -> {
                    if (status.confidence >= minConfidence) {
                        orphanCandidates.add(contentId to status)
                    }
                }
                is OrphanStatus.Active -> {
                    // Skip active content
                }
            }
        }

        // Sort by confidence (orphaned first, then by confidence level)
        return orphanCandidates.sortedWith(compareBy(
            { it.second !is OrphanStatus.Orphaned },
            {
                when (val s = it.second) {
                    is OrphanStatus.Uncertain -> -s.confidence
                    else -> 0f
                }
            }
        ))
    }

    /**
     * Analyze orphan patterns and provide statistics
     */
    fun analyzeOrphanPatterns(
        contentIds: List<Int>? = null
    ): OrphanAnalysisReport {
        val referenceMap = buildReferenceMap()

        // If no content IDs provided, try to get all from content storage
        val idsToCheck = contentIds ?: try {
            ContentStorageReader.open(cachesDir).use { reader ->
                reader.listContentIds()
            }
        } catch (e: Exception) {
            println("Warning: Could not read content storage: ${e.message}")
            emptyList()
        }

        var totalContent = 0
        var orphanedCount = 0
        var activeCount = 0
        var uncertainCount = 0
        val uncertainByConfidence = mutableMapOf<String, Int>()
        val orphanedByAge = mutableMapOf<String, Int>()

        for (contentId in idsToCheck) {
            totalContent++
            val status = checkOrphanStatus(contentId, referenceMap)

            when (status) {
                is OrphanStatus.Orphaned -> {
                    orphanedCount++
                    // Categorize by age of last reference
                    val refs = referenceMap[contentId]
                    val lastRef = refs?.maxByOrNull { it.timestamp ?: 0 }
                    lastRef?.timestampInstant?.let {
                        val daysSince = ChronoUnit.DAYS.between(it, Instant.now())
                        val ageCategory = when {
                            daysSince < 7 -> "< 1 week"
                            daysSince < 30 -> "1-4 weeks"
                            daysSince < 90 -> "1-3 months"
                            else -> "> 3 months"
                        }
                        orphanedByAge[ageCategory] = orphanedByAge.getOrDefault(ageCategory, 0) + 1
                    }
                }
                is OrphanStatus.Active -> activeCount++
                is OrphanStatus.Uncertain -> {
                    uncertainCount++
                    val confidenceLevel = when {
                        status.confidence >= HIGH_CONFIDENCE -> "High (>90%)"
                        status.confidence >= MEDIUM_CONFIDENCE -> "Medium (70-90%)"
                        else -> "Low (<70%)"
                    }
                    uncertainByConfidence[confidenceLevel] =
                        uncertainByConfidence.getOrDefault(confidenceLevel, 0) + 1
                }
            }
        }

        return OrphanAnalysisReport(
            totalContent = totalContent,
            orphanedCount = orphanedCount,
            activeCount = activeCount,
            uncertainCount = uncertainCount,
            uncertainByConfidence = uncertainByConfidence,
            orphanedByAge = orphanedByAge,
            referenceMapSize = referenceMap.size
        )
    }

    /**
     * Get detailed orphan information for a specific content ID
     */
    fun getOrphanDetails(contentId: Int): OrphanDetails {
        val references = findReferences(contentId)
        val referenceMap = mapOf(contentId to references)
        val status = checkOrphanStatus(contentId, referenceMap)

        // Try to read actual content
        val content = try {
            ContentStorageReader.open(cachesDir).use { reader ->
                reader.readContent(contentId)
            }
        } catch (e: Exception) {
            null
        }

        return OrphanDetails(
            contentId = contentId,
            status = status,
            references = references,
            contentSize = content?.content?.size,
            contentHash = content?.cryptoHashHex,
            isCompressed = content?.isCompressed,
            lastReferencePath = references.firstOrNull { it.path != null }?.path,
            lastReferenceTime = references.maxByOrNull { it.timestamp ?: 0 }?.timestampInstant
        )
    }
}

/**
 * Report of orphan analysis across multiple content items
 */
data class OrphanAnalysisReport(
    val totalContent: Int,
    val orphanedCount: Int,
    val activeCount: Int,
    val uncertainCount: Int,
    val uncertainByConfidence: Map<String, Int>,
    val orphanedByAge: Map<String, Int>,
    val referenceMapSize: Int
) {
    val orphanPercentage: Float
        get() = if (totalContent > 0) (orphanedCount * 100f) / totalContent else 0f

    val activePercentage: Float
        get() = if (totalContent > 0) (activeCount * 100f) / totalContent else 0f

    fun printSummary() {
        println("=== Orphan Analysis Report ===")
        println("Total content items: $totalContent")
        println("Reference map entries: $referenceMapSize")
        println()
        println("Status breakdown:")
        println("  Active: $activeCount (${String.format("%.1f", activePercentage)}%)")
        println("  Orphaned: $orphanedCount (${String.format("%.1f", orphanPercentage)}%)")
        println("  Uncertain: $uncertainCount")

        if (uncertainByConfidence.isNotEmpty()) {
            println()
            println("Uncertain by confidence:")
            uncertainByConfidence.forEach { (level, count) ->
                println("  $level: $count")
            }
        }

        if (orphanedByAge.isNotEmpty()) {
            println()
            println("Orphaned content by age:")
            orphanedByAge.forEach { (age, count) ->
                println("  $age: $count")
            }
        }
    }
}

/**
 * Detailed information about a specific potentially orphaned content
 */
data class OrphanDetails(
    val contentId: Int,
    val status: OrphanStatus,
    val references: List<ContentReference>,
    val contentSize: Int?,
    val contentHash: String?,
    val isCompressed: Boolean?,
    val lastReferencePath: String?,
    val lastReferenceTime: Instant?
) {
    fun printDetails() {
        println("=== Orphan Details for Content ID $contentId ===")
        println("Status: $status")
        println("References found: ${references.size}")
        contentSize?.let { println("Content size: $it bytes") }
        contentHash?.let { println("Content hash: $it") }
        isCompressed?.let { println("Compressed: $it") }
        lastReferencePath?.let { println("Last referenced path: $it") }
        lastReferenceTime?.let { println("Last reference time: $it") }

        if (references.isNotEmpty()) {
            println()
            println("Reference history:")
            references.take(10).forEach { ref ->
                println("  ${ref.timestampInstant ?: "Unknown time"}: ${ref.changeType} - ${ref.path ?: "Unknown path"}")
            }
            if (references.size > 10) {
                println("  ... and ${references.size - 10} more references")
            }
        }
    }
}