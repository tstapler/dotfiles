package com.stapler.localhistory.analyzer

import com.stapler.localhistory.facade.LocalHistoryFacade
import com.stapler.localhistory.facade.LocalHistoryFacadeFactory
import com.stapler.localhistory.model.ChangeType
import java.nio.file.Path

/**
 * LocalHistory reader that uses the facade API.
 *
 * This implementation delegates to a LocalHistoryFacade, which provides
 * better format compatibility and abstraction over storage details.
 */
class FacadeLocalHistoryReader(
    localHistoryPath: Path,
    cachesPath: Path
) : LocalHistoryReader {

    private val facade: LocalHistoryFacade = LocalHistoryFacadeFactory.create(localHistoryPath, cachesPath)

    override fun buildReferenceMap(): Map<Int, List<ContentReference>> {
        val facadeMap = facade.buildContentReferenceMap()

        // Convert facade Change objects to ContentReference objects
        return facadeMap.mapValues { (_, changes) ->
            changes.map { change ->
                ContentReference(
                    contentId = change.contentId ?: 0,
                    path = change.path,
                    timestamp = change.timestamp,
                    changeType = changeTypeToString(change.type)
                )
            }
        }
    }

    override fun getImplementationName(): String = "Facade API (${facade.getImplementationType()})"

    override fun close() {
        facade.close()
    }

    /**
     * Search for changes by path (facade-specific feature).
     */
    fun searchByPath(searchTerm: String, limit: Int = 100) = facade.searchByPath(searchTerm, limit)

    private fun changeTypeToString(type: ChangeType): String = when (type) {
        ChangeType.CREATE_FILE -> "CreateFile"
        ChangeType.CREATE_DIRECTORY -> "CreateDirectory"
        ChangeType.CONTENT_CHANGE -> "ContentChange"
        ChangeType.RENAME -> "Rename"
        ChangeType.RO_STATUS_CHANGE -> "ROStatusChange"
        ChangeType.MOVE -> "Move"
        ChangeType.DELETE -> "Delete"
        ChangeType.PUT_LABEL -> "PutLabel"
        ChangeType.PUT_SYSTEM_LABEL -> "PutSystemLabel"
        ChangeType.UNKNOWN -> "Unknown"
    }
}
