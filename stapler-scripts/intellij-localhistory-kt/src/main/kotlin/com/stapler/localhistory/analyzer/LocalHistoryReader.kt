package com.stapler.localhistory.analyzer

import java.io.Closeable

/**
 * Abstraction for reading LocalHistory data.
 *
 * This interface enables the OrphanDetector to work with different
 * LocalHistory reading strategies (direct file parsing vs facade API).
 */
interface LocalHistoryReader : Closeable {

    /**
     * Build a map of content ID -> references from LocalHistory.
     *
     * @return Map where keys are content IDs and values are lists of references to that content
     */
    fun buildReferenceMap(): Map<Int, List<ContentReference>>

    /**
     * Get implementation name for debugging/logging.
     */
    fun getImplementationName(): String

    /**
     * Default close implementation for readers that don't need cleanup.
     */
    override fun close() {}
}
