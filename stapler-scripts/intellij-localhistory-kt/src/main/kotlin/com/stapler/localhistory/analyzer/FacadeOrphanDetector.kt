package com.stapler.localhistory.analyzer

import java.nio.file.Path

/**
 * Orphan detector that uses the LocalHistoryFacade for improved reliability.
 *
 * This is now a thin wrapper around OrphanDetector with FacadeLocalHistoryReader,
 * providing backward compatibility with the original API.
 *
 * Most functionality is inherited from OrphanDetector. This class adds:
 * - searchByPath: Facade-specific path search capability
 * - getFacadeInfo: Get information about the underlying facade
 *
 * @see OrphanDetector.withFacade for the recommended way to create facade-based detectors
 */
class FacadeOrphanDetector(
    private val localHistoryDir: Path,
    private val cachesDir: Path
) : OrphanDetector(
    localHistoryDir,
    cachesDir,
    FacadeLocalHistoryReader(localHistoryDir, cachesDir)
) {
    // Store our own reader for facade-specific operations
    private val facadeReader = FacadeLocalHistoryReader(localHistoryDir, cachesDir)

    /**
     * Search for content changes matching a path pattern.
     * This is a facade-specific operation not available in the base class.
     */
    fun searchByPath(searchTerm: String, limit: Int = 100): List<ContentReference> {
        val results = facadeReader.searchByPath(searchTerm, limit)
        return results.map { (changeSet, change) ->
            ContentReference(
                contentId = change.contentId ?: 0,
                path = change.path,
                timestamp = changeSet.timestamp,
                changeType = change.type.name
            )
        }
    }

    /**
     * Get facade implementation info for debugging.
     */
    fun getFacadeInfo(): String = facadeReader.getImplementationName()

    /**
     * Close the facade and release resources.
     */
    fun close() {
        facadeReader.close()
    }
}
