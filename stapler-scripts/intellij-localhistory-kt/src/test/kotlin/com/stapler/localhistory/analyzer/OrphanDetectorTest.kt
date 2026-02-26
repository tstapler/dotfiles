package com.stapler.localhistory.analyzer

import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*
import java.nio.file.Path
import java.time.Instant
import java.time.temporal.ChronoUnit

/**
 * Tests for OrphanDetector using the composition-based LocalHistoryReader pattern.
 */
class OrphanDetectorTest {

    /**
     * Mock LocalHistoryReader for testing without actual files.
     */
    private class MockLocalHistoryReader(
        private val referenceMap: Map<Int, List<ContentReference>> = emptyMap()
    ) : LocalHistoryReader {
        override fun buildReferenceMap() = referenceMap
        override fun getImplementationName() = "Mock Reader"
    }

    private fun createDetector(referenceMap: Map<Int, List<ContentReference>> = emptyMap()): OrphanDetector {
        return OrphanDetector(
            Path.of("/mock/localhistory"),
            Path.of("/mock/caches"),
            MockLocalHistoryReader(referenceMap)
        )
    }

    @Test
    fun `test orphan status for content with no references`() {
        val detector = createDetector()
        val status = detector.checkOrphanStatus(1, emptyMap())

        assertTrue(status is OrphanStatus.Uncertain)
        val uncertain = status as OrphanStatus.Uncertain
        assertEquals(0.9f, uncertain.confidence)
        assertTrue(uncertain.reason.contains("No references"))
    }

    @Test
    fun `test orphan status for content with only delete references`() {
        val references = listOf(
            ContentReference(1, "/test/file.txt", System.currentTimeMillis(), "Delete")
        )
        val referenceMap = mapOf(1 to references)
        val detector = createDetector(referenceMap)
        val status = detector.checkOrphanStatus(1, referenceMap)

        assertTrue(status is OrphanStatus.Orphaned)
    }

    @Test
    fun `test active status for content with recent ContentChange`() {
        val now = System.currentTimeMillis()
        val references = listOf(
            ContentReference(1, "/test/file.txt", now - 1000, "ContentChange")
        )
        val referenceMap = mapOf(1 to references)
        val detector = createDetector(referenceMap)
        val status = detector.checkOrphanStatus(1, referenceMap)

        assertTrue(status is OrphanStatus.Active)
    }

    @Test
    fun `test uncertain status for old content references`() {
        val oldTimestamp = Instant.now().minus(60, ChronoUnit.DAYS).toEpochMilli()
        val references = listOf(
            ContentReference(1, "/test/file.txt", oldTimestamp, "ContentChange")
        )
        val referenceMap = mapOf(1 to references)
        val detector = createDetector(referenceMap)
        val status = detector.checkOrphanStatus(1, referenceMap)

        assertTrue(status is OrphanStatus.Uncertain)
        val uncertain = status as OrphanStatus.Uncertain
        assertTrue(uncertain.confidence >= 0.7f)
        assertTrue(uncertain.reason.contains("days"))
    }

    @Test
    fun `test orphaned status when delete is after content change`() {
        val now = System.currentTimeMillis()
        val references = listOf(
            ContentReference(1, "/test/file.txt", now - 10000, "ContentChange"),
            ContentReference(1, "/test/file.txt", now - 5000, "Delete")
        )
        val referenceMap = mapOf(1 to references)
        val detector = createDetector(referenceMap)
        val status = detector.checkOrphanStatus(1, referenceMap)

        assertTrue(status is OrphanStatus.Orphaned)
    }

    @Test
    fun `test active status when content change is after delete`() {
        val now = System.currentTimeMillis()
        val references = listOf(
            ContentReference(1, "/test/file.txt", now - 10000, "Delete"),
            ContentReference(1, "/test/file.txt", now - 5000, "ContentChange")
        )
        val referenceMap = mapOf(1 to references)
        val detector = createDetector(referenceMap)
        val status = detector.checkOrphanStatus(1, referenceMap)

        assertTrue(status is OrphanStatus.Active)
    }

    @Test
    fun `test findOrphanedContent filters by confidence`() {
        // Create mock reference map with various statuses
        val mockReferenceMap = mapOf(
            1 to listOf(ContentReference(1, "/active.txt", System.currentTimeMillis(), "ContentChange")),
            2 to listOf(ContentReference(2, "/deleted.txt", System.currentTimeMillis(), "Delete")),
            3 to emptyList<ContentReference>()
        )

        val detector = createDetector(mockReferenceMap)
        val contentIds = listOf(1, 2, 3)

        // Build the reference map first, then find orphans
        val builtMap = detector.buildReferenceMap()
        val orphans = contentIds.mapNotNull { id ->
            val status = detector.checkOrphanStatus(id, builtMap)
            when (status) {
                is OrphanStatus.Orphaned -> id to status
                is OrphanStatus.Uncertain -> if (status.confidence >= 0.8f) id to status else null
                is OrphanStatus.Active -> null
            }
        }

        // Should include orphaned (ID 2) and high-confidence uncertain (ID 3)
        assertEquals(2, orphans.size)
        assertTrue(orphans.any { it.first == 2 })
        assertTrue(orphans.any { it.first == 3 })

        // Should not include active (ID 1)
        assertFalse(orphans.any { it.first == 1 })
    }

    @Test
    fun `test getReaderName returns implementation name`() {
        val detector = createDetector()
        assertEquals("Mock Reader", detector.getReaderName())
    }

    @Test
    fun `test buildReferenceMap delegates to reader`() {
        val expectedMap = mapOf(
            1 to listOf(ContentReference(1, "/test.txt", System.currentTimeMillis(), "ContentChange"))
        )
        val detector = createDetector(expectedMap)

        val actualMap = detector.buildReferenceMap()
        assertEquals(expectedMap, actualMap)
    }

    @Test
    fun `test very old content should be uncertain with high confidence`() {
        val veryOldTimestamp = Instant.now().minus(120, ChronoUnit.DAYS).toEpochMilli()
        val references = listOf(
            ContentReference(1, "/test/file.txt", veryOldTimestamp, "ContentChange")
        )
        val referenceMap = mapOf(1 to references)
        val detector = createDetector(referenceMap)
        val status = detector.checkOrphanStatus(1, referenceMap)

        assertTrue(status is OrphanStatus.Uncertain)
        val uncertain = status as OrphanStatus.Uncertain
        assertEquals(OrphanDetector.HIGH_CONFIDENCE, uncertain.confidence)
    }
}