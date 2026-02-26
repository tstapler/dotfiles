package com.stapler.localhistory.parser

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Variable-length integer reader matching IntelliJ's encoding format.
 *
 * IntelliJ uses a custom variable-length integer encoding that optimizes
 * for small values while supporting the full int32 range:
 *
 * - 0-30: Single byte (values 0x00-0x1E)
 * - 31: Sentinel for full 4-byte int (0x1F followed by 4 bytes)
 * - 32-63: 3-byte encoding (0x20-0x3F prefix)
 * - 64-127: 4-byte encoding (0x40-0x7F prefix)
 * - 128-191: Single byte offset by 128 (0x80-0xBF)
 * - 192-255: 2-byte encoding (0xC0-0xFF prefix)
 *
 * This is a consolidated implementation used across all parsing code.
 */
class VarIntReader(private val data: ByteArray, private var offset: Int = 0) {

    /**
     * Read a variable-length integer from the current position.
     * Advances the offset past the read value.
     *
     * @return The decoded integer value, or 0 if reading beyond bounds
     */
    fun readVarInt(): Int {
        if (offset >= data.size) return 0

        val b = data[offset].toInt() and 0xFF
        return when {
            // 2-byte encoding: first 6 bits from prefix, 8 bits from next byte
            b >= 192 -> {
                offset += 2
                if (offset > data.size) return 0
                ((b - 192) shl 8) or (data[offset - 1].toInt() and 0xFF)
            }
            // Single byte offset by 128
            b >= 128 -> {
                offset++
                b - 128
            }
            // 4-byte encoding: first 6 bits from prefix, 24 bits from next 3 bytes
            b >= 64 -> {
                offset += 4
                if (offset > data.size) return 0
                ((b - 64) shl 24) or
                    ((data[offset - 3].toInt() and 0xFF) shl 16) or
                    ((data[offset - 2].toInt() and 0xFF) shl 8) or
                    (data[offset - 1].toInt() and 0xFF)
            }
            // 3-byte encoding: first 5 bits from prefix, 16 bits from next 2 bytes
            b >= 32 -> {
                offset += 3
                if (offset > data.size) return 0
                ((b - 32) shl 16) or
                    ((data[offset - 2].toInt() and 0xFF) shl 8) or
                    (data[offset - 1].toInt() and 0xFF)
            }
            // Sentinel for full 4-byte big-endian int
            b == 31 -> {
                offset += 5
                if (offset > data.size) return 0
                ByteBuffer.wrap(data, offset - 4, 4).order(ByteOrder.BIG_ENDIAN).int
            }
            // Direct single-byte value (0-30)
            else -> {
                offset++
                b
            }
        }
    }

    /**
     * Read a variable-length long.
     * Note: Currently simplified to read as VarInt - suitable for timestamps
     * that fit in 32 bits when stored relative to epoch.
     */
    fun readVarLong(): Long = readVarInt().toLong()

    /**
     * Read a length-prefixed UTF-8 string.
     *
     * @return The decoded string, or empty string if length is 0 or invalid
     */
    fun readString(): String {
        val length = readVarInt()
        if (length == 0 || offset + length > data.size) return ""
        val str = String(data, offset, length, Charsets.UTF_8)
        offset += length
        return str
    }

    /**
     * Read an optional string (prefixed by boolean flag).
     *
     * @return The decoded string if present, null otherwise
     */
    fun readStringOrNull(): String? {
        if (offset >= data.size) return null
        val hasValue = data[offset++].toInt() != 0
        return if (hasValue) readString() else null
    }

    /**
     * Read a single boolean byte.
     */
    fun readBoolean(): Boolean = if (offset < data.size) data[offset++].toInt() != 0 else false

    /**
     * Get the current read position.
     */
    fun currentOffset(): Int = offset

    /**
     * Check if more data is available.
     */
    fun hasMore(): Boolean = offset < data.size

    /**
     * Skip a specified number of bytes.
     */
    fun skip(n: Int) {
        offset += n
    }

    /**
     * Get current position (alias for currentOffset for compatibility).
     */
    fun position(): Int = offset
}
