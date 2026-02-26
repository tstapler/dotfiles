package com.stapler.localhistory.analyzer

import com.stapler.localhistory.parser.parseDataFile
import com.stapler.localhistory.parser.parseIndexFile
import java.nio.file.Path
import kotlin.io.path.exists

/**
 * LocalHistory reader that directly parses storage files.
 *
 * This implementation reads the changes.storageRecordIndex and changes.storageData
 * files directly without using the facade API.
 */
class DirectLocalHistoryReader(
    private val localHistoryDir: Path
) : LocalHistoryReader {

    override fun buildReferenceMap(): Map<Int, List<ContentReference>> {
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

    override fun getImplementationName(): String = "Direct File Parser"
}
