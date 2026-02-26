package com.stapler.localhistory.parser

import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*

/**
 * Tests for VarIntReader - the variable-length integer parser.
 *
 * Tests the IntelliJ-compatible VarInt encoding scheme:
 * - 0-30: Single byte
 * - 31: Sentinel for full 4-byte int
 * - 32-63: 3-byte encoding
 * - 64-127: 4-byte encoding
 * - 128-191: Single byte offset by 128
 * - 192-255: 2-byte encoding
 */
class VarIntReaderTest {

    @Test
    fun `should read single byte values 0-30`() {
        // Values 0-30 are encoded as themselves
        for (value in 0..30) {
            val reader = VarIntReader(byteArrayOf(value.toByte()))
            assertEquals(value, reader.readVarInt())
            assertEquals(1, reader.currentOffset())
        }
    }

    @Test
    fun `should read single byte values 128-191 as offset by 128`() {
        // Bytes 128-191 (0x80-0xBF) encode values 0-63
        for (i in 0..63) {
            val encodedByte = (128 + i).toByte()
            val reader = VarIntReader(byteArrayOf(encodedByte))
            assertEquals(i, reader.readVarInt())
            assertEquals(1, reader.currentOffset())
        }
    }

    @Test
    fun `should read two byte values with 192-255 prefix`() {
        // Two-byte encoding: (prefix - 192) << 8 | nextByte
        // Example: [200, 100] = (200-192) << 8 | 100 = 8 << 8 | 100 = 2148
        val reader = VarIntReader(byteArrayOf(200.toByte(), 100.toByte()))
        val expected = ((200 - 192) shl 8) or 100
        assertEquals(expected, reader.readVarInt())
        assertEquals(2, reader.currentOffset())
    }

    @Test
    fun `should read three byte values with 32-63 prefix`() {
        // Three-byte encoding: (prefix - 32) << 16 | byte1 << 8 | byte2
        val reader = VarIntReader(byteArrayOf(40.toByte(), 1.toByte(), 2.toByte()))
        val expected = ((40 - 32) shl 16) or (1 shl 8) or 2
        assertEquals(expected, reader.readVarInt())
        assertEquals(3, reader.currentOffset())
    }

    @Test
    fun `should read four byte values with 64-127 prefix`() {
        // Four-byte encoding: (prefix - 64) << 24 | byte1 << 16 | byte2 << 8 | byte3
        val reader = VarIntReader(byteArrayOf(70.toByte(), 0.toByte(), 1.toByte(), 0.toByte()))
        val expected = ((70 - 64) shl 24) or (0 shl 16) or (1 shl 8) or 0
        assertEquals(expected, reader.readVarInt())
        assertEquals(4, reader.currentOffset())
    }

    @Test
    fun `should handle empty data gracefully`() {
        val reader = VarIntReader(byteArrayOf())
        assertEquals(0, reader.readVarInt())
        assertFalse(reader.hasMore())
    }

    @Test
    fun `should read string correctly`() {
        // Length-prefixed string: [length][bytes...]
        val testString = "Hello"
        val data = byteArrayOf(5.toByte()) + testString.toByteArray(Charsets.UTF_8)
        val reader = VarIntReader(data)
        assertEquals(testString, reader.readString())
    }

    @Test
    fun `should read empty string when length is 0`() {
        val reader = VarIntReader(byteArrayOf(0.toByte()))
        assertEquals("", reader.readString())
    }

    @Test
    fun `should read nullable string`() {
        // Nullable string: [0 = null] or [1][length][bytes...]
        val nullReader = VarIntReader(byteArrayOf(0.toByte()))
        assertNull(nullReader.readStringOrNull())

        val testString = "Test"
        val data = byteArrayOf(1.toByte(), 4.toByte()) + testString.toByteArray(Charsets.UTF_8)
        val nonNullReader = VarIntReader(data)
        assertEquals(testString, nonNullReader.readStringOrNull())
    }

    @Test
    fun `should track position correctly through multiple reads`() {
        // Multiple values: [5][0][200, 100]
        val data = byteArrayOf(5.toByte(), 0.toByte(), 200.toByte(), 100.toByte())
        val reader = VarIntReader(data)

        assertEquals(0, reader.currentOffset())
        reader.readVarInt() // reads 5
        assertEquals(1, reader.currentOffset())
        reader.readVarInt() // reads 0
        assertEquals(2, reader.currentOffset())
        reader.readVarInt() // reads 2-byte value
        assertEquals(4, reader.currentOffset())
        assertFalse(reader.hasMore())
    }

    @Test
    fun `should read boolean values`() {
        val reader = VarIntReader(byteArrayOf(0.toByte(), 1.toByte(), 255.toByte()))
        assertFalse(reader.readBoolean())
        assertTrue(reader.readBoolean())
        assertTrue(reader.readBoolean()) // 255 != 0, so true
    }

    @Test
    fun `should skip bytes correctly`() {
        val reader = VarIntReader(byteArrayOf(1, 2, 3, 4, 5))
        reader.skip(3)
        assertEquals(3, reader.currentOffset())
        assertEquals(4, reader.readVarInt())
    }

    @Test
    fun `hasMore should work correctly`() {
        val reader = VarIntReader(byteArrayOf(1, 2))
        assertTrue(reader.hasMore())
        reader.readVarInt()
        assertTrue(reader.hasMore())
        reader.readVarInt()
        assertFalse(reader.hasMore())
    }
}
