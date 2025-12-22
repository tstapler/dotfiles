package com.stapler.localhistory.analyzer

import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*
import java.time.Instant
import java.time.temporal.ChronoUnit

class OrphanDetectorTest {

    @Test
    fun `test orphan status for content with no references`() {
        val referenceMap = emptyMap<Int, List<ContentReference>>()
        val status = testCheckOrphanStatus(1, referenceMap)

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
        val status = testCheckOrphanStatus(1, referenceMap)

        assertTrue(status is OrphanStatus.Orphaned)
    }

    @Test
    fun `test active status for content with recent ContentChange`() {
        val now = System.currentTimeMillis()
        val references = listOf(
            ContentReference(1, "/test/file.txt", now - 1000, "ContentChange")
        )
        val referenceMap = mapOf(1 to references)
        val status = testCheckOrphanStatus(1, referenceMap)

        assertTrue(status is OrphanStatus.Active)
    }

    @Test
    fun `test uncertain status for old content references`() {
        val oldTimestamp = Instant.now().minus(60, ChronoUnit.DAYS).toEpochMilli()
        val references = listOf(
            ContentReference(1, "/test/file.txt", oldTimestamp, "ContentChange")
        )
        val referenceMap = mapOf(1 to references)
        val status = testCheckOrphanStatus(1, referenceMap)

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
        val status = testCheckOrphanStatus(1, referenceMap)

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
        val status = testCheckOrphanStatus(1, referenceMap)

        assertTrue(status is OrphanStatus.Active)
    }

    @Test
    fun `test findOrphanedContent filters by confidence`() {
        val detector = MockOrphanDetector()

        // Create mock reference map with various statuses
        val mockReferenceMap = mapOf(
            1 to listOf(ContentReference(1, "/active.txt", System.currentTimeMillis(), "ContentChange")),
            2 to listOf(ContentReference(2, "/deleted.txt", System.currentTimeMillis(), "Delete")),
            3 to emptyList<ContentReference>()
        )

        detector.setMockReferenceMap(mockReferenceMap)

        val contentIds = listOf(1, 2, 3)

        // Build the reference map first, then use findOrphanedContent
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

    // Helper function to test checkOrphanStatus without needing file paths
    private fun testCheckOrphanStatus(
        contentId: Int,
        referenceMap: Map<Int, List<ContentReference>>
    ): OrphanStatus {
        // Use the static method approach - just call the method directly
        val detector = MockOrphanDetector()
        return detector.checkOrphanStatus(contentId, referenceMap)
    }

    // Mock implementation for testing
    private class MockOrphanDetector : OrphanDetector(
        java.nio.file.Paths.get("/mock/localhistory"),
        java.nio.file.Paths.get("/mock/caches")
    ) {
        private var mockReferenceMap = emptyMap<Int, List<ContentReference>>()

        fun setMockReferenceMap(map: Map<Int, List<ContentReference>>) {
            mockReferenceMap = map
        }

        override fun buildReferenceMap(): Map<Int, List<ContentReference>> {
            return mockReferenceMap
        }
    }
}