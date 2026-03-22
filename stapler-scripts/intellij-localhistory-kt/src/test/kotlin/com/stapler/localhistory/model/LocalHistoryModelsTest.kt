package com.stapler.localhistory.model

import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*

/**
 * Tests for the unified LocalHistory domain models.
 */
class LocalHistoryModelsTest {

    @Test
    fun `ChangeType fromId should map correctly`() {
        assertEquals(ChangeType.CREATE_FILE, ChangeType.fromId(1))
        assertEquals(ChangeType.CREATE_DIRECTORY, ChangeType.fromId(2))
        assertEquals(ChangeType.CONTENT_CHANGE, ChangeType.fromId(3))
        assertEquals(ChangeType.RENAME, ChangeType.fromId(4))
        assertEquals(ChangeType.RO_STATUS_CHANGE, ChangeType.fromId(5))
        assertEquals(ChangeType.MOVE, ChangeType.fromId(6))
        assertEquals(ChangeType.DELETE, ChangeType.fromId(7))
        assertEquals(ChangeType.PUT_LABEL, ChangeType.fromId(8))
        assertEquals(ChangeType.PUT_SYSTEM_LABEL, ChangeType.fromId(9))
        assertEquals(ChangeType.UNKNOWN, ChangeType.fromId(0))
        assertEquals(ChangeType.UNKNOWN, ChangeType.fromId(999))
    }

    @Test
    fun `ChangeType fromName should map correctly`() {
        assertEquals(ChangeType.CREATE_FILE, ChangeType.fromName("CreateFile"))
        assertEquals(ChangeType.CREATE_DIRECTORY, ChangeType.fromName("CreateDirectory"))
        assertEquals(ChangeType.CONTENT_CHANGE, ChangeType.fromName("ContentChange"))
        assertEquals(ChangeType.RENAME, ChangeType.fromName("Rename"))
        assertEquals(ChangeType.DELETE, ChangeType.fromName("Delete"))
        assertEquals(ChangeType.UNKNOWN, ChangeType.fromName("InvalidType"))
    }

    @Test
    fun `ChangeType toName should produce correct strings`() {
        assertEquals("CreateFile", ChangeType.toName(ChangeType.CREATE_FILE))
        assertEquals("ContentChange", ChangeType.toName(ChangeType.CONTENT_CHANGE))
        assertEquals("Delete", ChangeType.toName(ChangeType.DELETE))
        assertEquals("Unknown", ChangeType.toName(ChangeType.UNKNOWN))
    }

    @Test
    fun `Change hasContent should detect content correctly`() {
        val withContent = Change(ChangeType.CONTENT_CHANGE, "/path/file.txt", 123)
        assertTrue(withContent.hasContent)

        val withoutContent = Change(ChangeType.DELETE, "/path/file.txt", null)
        assertFalse(withoutContent.hasContent)

        val withZeroContent = Change(ChangeType.CONTENT_CHANGE, "/path/file.txt", 0)
        assertFalse(withZeroContent.hasContent)
    }

    @Test
    fun `Change typeString should return display name`() {
        val change = Change(ChangeType.CONTENT_CHANGE, "/path/file.txt", 123)
        assertEquals("ContentChange", change.typeString)
    }

    @Test
    fun `ChangeSet should calculate affected paths correctly`() {
        val changes = listOf(
            Change(ChangeType.CONTENT_CHANGE, "/path/a.txt", 1),
            Change(ChangeType.CREATE_FILE, "/path/b.txt", 2),
            Change(ChangeType.DELETE, null, null)
        )
        val changeSet = ChangeSet(1L, "Test", System.currentTimeMillis(), changes)

        val paths = changeSet.affectedPaths
        assertEquals(2, paths.size)
        assertTrue(paths.contains("/path/a.txt"))
        assertTrue(paths.contains("/path/b.txt"))
    }

    @Test
    fun `ChangeSet should detect content changes and deletions`() {
        val withContent = ChangeSet(
            1L, "Test", System.currentTimeMillis(),
            listOf(Change(ChangeType.CONTENT_CHANGE, "/path/file.txt", 123))
        )
        assertTrue(withContent.hasContentChanges)
        assertFalse(withContent.hasDeletions)

        val withDeletion = ChangeSet(
            2L, "Test", System.currentTimeMillis(),
            listOf(Change(ChangeType.DELETE, "/path/file.txt", null))
        )
        assertFalse(withDeletion.hasContentChanges)
        assertTrue(withDeletion.hasDeletions)
    }

    @Test
    fun `ContentRecord isText should detect text content`() {
        val textContent = ContentRecord(1, "abc123", "Hello World!".toByteArray())
        assertTrue(textContent.isText())

        // Binary content with non-printable bytes
        val binaryContent = ContentRecord(2, "def456", byteArrayOf(0, 1, 2, 3, 4, 5))
        assertFalse(binaryContent.isText())

        // Empty content should be considered text
        val emptyContent = ContentRecord(3, "empty", byteArrayOf())
        assertTrue(emptyContent.isText())
    }

    @Test
    fun `ContentRecord contentAsString should convert correctly`() {
        val testString = "Hello, World!"
        val record = ContentRecord(1, "hash", testString.toByteArray(Charsets.UTF_8))
        assertEquals(testString, record.contentAsString())
    }

    @Test
    fun `ContentRecord equals and hashCode should work correctly`() {
        val record1 = ContentRecord(1, "hash1", "content".toByteArray())
        val record2 = ContentRecord(1, "hash1", "different".toByteArray())
        val record3 = ContentRecord(2, "hash1", "content".toByteArray())

        // Same id and hash = equal
        assertEquals(record1, record2)
        assertEquals(record1.hashCode(), record2.hashCode())

        // Different id = not equal
        assertNotEquals(record1, record3)
    }

    @Test
    fun `IndexRecord timestampStr should format correctly`() {
        val record = IndexRecord(1, 100L, 50, 64, 0, 2, 1700000000000L)
        assertNotEquals("N/A", record.timestampStr)
        assertTrue(record.timestampStr.contains("2023")) // Year 2023 for epoch 1700000000000

        val noTimestamp = IndexRecord(1, 100L, 50, 64, 0, 2, 0)
        assertEquals("N/A", noTimestamp.timestampStr)
    }
}
