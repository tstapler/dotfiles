package com.stapler.localhistory.facade

import java.nio.file.Path

// Re-export types from model package for backward compatibility
import com.stapler.localhistory.model.ChangeType
import com.stapler.localhistory.model.Change
import com.stapler.localhistory.model.ChangeSet
import com.stapler.localhistory.model.ChangeFilter
import com.stapler.localhistory.model.ContentRecord
import com.stapler.localhistory.model.LocalHistoryStats

// Make types available from this package for existing imports
typealias ChangeType = com.stapler.localhistory.model.ChangeType
typealias Change = com.stapler.localhistory.model.Change
typealias ChangeSet = com.stapler.localhistory.model.ChangeSet
typealias ChangeFilter = com.stapler.localhistory.model.ChangeFilter
typealias ContentRecord = com.stapler.localhistory.model.ContentRecord
typealias LocalHistoryStats = com.stapler.localhistory.model.LocalHistoryStats

/**
 * Facade for reading IntelliJ LocalHistory data
 *
 * This interface provides a clean abstraction over LocalHistory storage,
 * supporting multiple implementation strategies (IntelliJ API, custom parsing, etc.)
 */
interface LocalHistoryFacade : AutoCloseable {

    /**
     * Initialize the facade with paths to LocalHistory and caches directories
     */
    fun initialize(localHistoryPath: Path, cachesPath: Path)

    /**
     * Get change sets matching the filter criteria
     */
    fun getChangeSets(filter: ChangeFilter = ChangeFilter()): List<ChangeSet>

    /**
     * Search for changes affecting files matching the search term
     */
    fun searchByPath(searchTerm: String, limit: Int = 100): List<Pair<ChangeSet, Change>>

    /**
     * Get content by ID from the content storage
     */
    fun getContent(contentId: Int): ContentRecord?

    /**
     * Get all content IDs in the storage
     */
    fun listContentIds(): List<Int>

    /**
     * Get statistics about the LocalHistory storage
     */
    fun getStats(): LocalHistoryStats

    /**
     * Build a map of content ID to all changes referencing it
     */
    fun buildContentReferenceMap(): Map<Int, List<Change>>

    /**
     * Check if the facade is properly initialized and ready
     */
    fun isReady(): Boolean

    /**
     * Get the implementation type for debugging
     */
    fun getImplementationType(): String
}

/**
 * Factory for creating LocalHistoryFacade instances
 */
object LocalHistoryFacadeFactory {

    /**
     * Create a facade instance, automatically selecting the best implementation
     */
    fun create(localHistoryPath: Path, cachesPath: Path): LocalHistoryFacade {
        // Try IntelliJ API implementation first
        val intellijImpl = tryCreateIntelliJImpl()
        if (intellijImpl != null) {
            try {
                intellijImpl.initialize(localHistoryPath, cachesPath)
                if (intellijImpl.isReady()) {
                    return intellijImpl
                }
            } catch (e: Exception) {
                // Fall through to custom implementation
            }
        }

        // Fall back to custom parser implementation
        val customImpl = CustomParserLocalHistoryFacade()
        customImpl.initialize(localHistoryPath, cachesPath)
        return customImpl
    }

    /**
     * Create a specific implementation type
     */
    fun create(
        type: ImplementationType,
        localHistoryPath: Path,
        cachesPath: Path
    ): LocalHistoryFacade {
        val facade = when (type) {
            ImplementationType.INTELLIJ_API -> IntelliJStorageLocalHistoryFacade()
            ImplementationType.CUSTOM_PARSER -> CustomParserLocalHistoryFacade()
        }
        facade.initialize(localHistoryPath, cachesPath)
        return facade
    }

    private fun tryCreateIntelliJImpl(): LocalHistoryFacade? {
        return try {
            IntelliJStorageLocalHistoryFacade()
        } catch (e: Exception) {
            null
        }
    }

    enum class ImplementationType {
        INTELLIJ_API,
        CUSTOM_PARSER
    }
}
