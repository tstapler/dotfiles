package com.stapler.localhistory.export

import com.stapler.localhistory.scanner.ContentScanResult
import java.text.SimpleDateFormat
import java.util.*
import kotlin.math.min

/**
 * Export format options for LLM consumption
 */
enum class ExportFormat {
    Markdown, JSON, CSV
}

/**
 * Options for controlling export behavior
 */
data class ExportOptions(
    val format: ExportFormat = ExportFormat.Markdown,
    val includeContent: Boolean = false,
    val maxContentLength: Int = 1000,
    val includePrompt: Boolean = true,
    val groupByType: Boolean = true
)

/**
 * Summary statistics for content analysis
 */
data class ContentSummary(
    val totalRecords: Int,
    val textRecords: Int,
    val binaryRecords: Int,
    val totalSizeBytes: Long,
    val fileTypeDistribution: Map<String, Int>,
    val timeRange: Pair<Long, Long>?  // earliest, latest timestamps if available
)

/**
 * Represents a deletion event from local history
 */
data class DeletionEvent(
    val timestamp: Long,
    val path: String,
    val contentId: Int?
)

/**
 * Exporter for generating LLM-friendly content analysis reports
 *
 * Supports multiple export formats (Markdown, JSON, CSV) optimized for LLM consumption
 * with automatic prompt generation and pattern analysis capabilities.
 */
class LLMExporter {

    companion object {
        private const val MAX_PREVIEW_LENGTH = 500
        private val DATE_FORMAT = SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
    }

    /**
     * Export a list of scan results in the specified format
     *
     * @param results List of content scan results to export
     * @param options Export configuration options
     * @return Formatted export string
     */
    fun export(
        results: List<ContentScanResult>,
        options: ExportOptions = ExportOptions()
    ): String {
        return when (options.format) {
            ExportFormat.Markdown -> exportAsMarkdown(results, options)
            ExportFormat.JSON -> exportAsJson(results, options)
            ExportFormat.CSV -> exportAsCsv(results, options)
        }
    }

    /**
     * Generate a Claude-friendly analysis prompt for the content
     *
     * @param results List of content scan results
     * @param context Additional context about the analysis
     * @return Analysis prompt string
     */
    fun generateAnalysisPrompt(
        results: List<ContentScanResult>,
        context: String = ""
    ): String {
        val summary = generateSummary(results)
        val typeBreakdown = summary.fileTypeDistribution.entries
            .sortedByDescending { it.value }
            .take(5)
            .joinToString(", ") { "${it.key}: ${it.value}" }

        return buildString {
            appendLine("Please analyze this IntelliJ local history content and provide insights on:")
            appendLine()
            appendLine("## Dataset Overview")
            appendLine("- Total records: ${summary.totalRecords}")
            appendLine("- Text content: ${summary.textRecords} (${calculatePercentage(summary.textRecords, summary.totalRecords)}%)")
            appendLine("- Binary content: ${summary.binaryRecords} (${calculatePercentage(summary.binaryRecords, summary.totalRecords)}%)")
            appendLine("- Total size: ${formatBytes(summary.totalSizeBytes)}")
            appendLine("- Top file types: $typeBreakdown")

            if (context.isNotBlank()) {
                appendLine()
                appendLine("## Additional Context")
                appendLine(context)
            }

            appendLine()
            appendLine("## Analysis Requirements")
            appendLine("1. **Important Code Recovery**: Identify high-value code that should be prioritized for recovery")
            appendLine("2. **Deletion Patterns**: Analyze patterns in the deleted content (refactoring, cleanup, accidental deletion)")
            appendLine("3. **Risk Assessment**: Identify potential data loss risks or missing critical code")
            appendLine("4. **Recovery Recommendations**: Suggest which content should be recovered and why")
            appendLine("5. **Code Quality Insights**: Note any patterns in code quality or development practices")
            appendLine()
            appendLine("Please structure your analysis with clear sections and actionable recommendations.")
        }
    }

    /**
     * Export with deletion pattern analysis
     *
     * @param results List of content scan results
     * @param deletionEvents Optional list of deletion events for correlation
     * @param options Export configuration options
     * @return Formatted export with pattern analysis
     */
    fun exportWithPatternAnalysis(
        results: List<ContentScanResult>,
        deletionEvents: List<DeletionEvent>? = null,
        options: ExportOptions = ExportOptions()
    ): String {
        val baseExport = export(results, options)

        if (deletionEvents.isNullOrEmpty()) {
            return baseExport
        }

        // Analyze deletion patterns
        val patternAnalysis = analyzeDeletionPatterns(results, deletionEvents)

        return when (options.format) {
            ExportFormat.Markdown -> {
                buildString {
                    append(baseExport)
                    appendLine()
                    appendLine("## Deletion Pattern Analysis")
                    appendLine()
                    append(patternAnalysis)
                }
            }
            ExportFormat.JSON -> {
                // Add pattern analysis to JSON
                val jsonBase = baseExport.removeSuffix("}")
                "$jsonBase,\"patternAnalysis\":${patternAnalysisToJson(patternAnalysis)}}"
            }
            ExportFormat.CSV -> {
                // CSV doesn't support nested analysis well, append as comment
                "$baseExport\n# Pattern Analysis:\n# ${patternAnalysis.replace("\n", "\n# ")}"
            }
        }
    }

    /**
     * Generate summary statistics for the content
     *
     * @param results List of content scan results
     * @return Content summary with statistics
     */
    fun generateSummary(results: List<ContentScanResult>): ContentSummary {
        val textRecords = results.count { it.metadata.isText }
        val binaryRecords = results.size - textRecords
        val totalSize = results.sumOf { it.metadata.size.toLong() }

        val fileTypeDistribution = results
            .groupingBy { it.fileType ?: "unknown" }
            .eachCount()

        // For now, we don't have timestamp data in ContentScanResult
        // This could be enhanced if timestamp data becomes available
        val timeRange: Pair<Long, Long>? = null

        return ContentSummary(
            totalRecords = results.size,
            textRecords = textRecords,
            binaryRecords = binaryRecords,
            totalSizeBytes = totalSize,
            fileTypeDistribution = fileTypeDistribution,
            timeRange = timeRange
        )
    }

    // Private helper methods

    private fun exportAsMarkdown(
        results: List<ContentScanResult>,
        options: ExportOptions
    ): String {
        val summary = generateSummary(results)

        return buildString {
            appendLine("# IntelliJ Content Analysis Report")
            appendLine()
            appendLine("## Summary")
            appendLine("- Total records: ${summary.totalRecords}")
            appendLine("- Text content: ${summary.textRecords} (${calculatePercentage(summary.textRecords, summary.totalRecords)}%)")
            appendLine("- Binary content: ${summary.binaryRecords} (${calculatePercentage(summary.binaryRecords, summary.totalRecords)}%)")
            appendLine("- Total size: ${formatBytes(summary.totalSizeBytes)}")
            appendLine()

            appendLine("## Content Type Distribution")
            appendLine("| Type | Count | Percentage |")
            appendLine("|------|-------|------------|")
            summary.fileTypeDistribution.entries
                .sortedByDescending { it.value }
                .forEach { (type, count) ->
                    val percentage = calculatePercentage(count, summary.totalRecords)
                    appendLine("| ${type.capitalize()} | $count | $percentage% |")
                }
            appendLine()

            // Group content by type if requested
            if (options.groupByType) {
                val groupedResults = results.groupBy { it.fileType ?: "unknown" }

                groupedResults.forEach { (type, typeResults) ->
                    appendLine("## ${type.capitalize()} Content (${typeResults.size} records)")
                    appendLine()

                    typeResults.take(10).forEach { result ->
                        appendMarkdownRecord(this, result, options)
                    }

                    if (typeResults.size > 10) {
                        appendLine("_... and ${typeResults.size - 10} more ${type} records_")
                        appendLine()
                    }
                }
            } else {
                appendLine("## Orphaned Content Samples")
                appendLine()

                results.take(20).forEach { result ->
                    appendMarkdownRecord(this, result, options)
                }

                if (results.size > 20) {
                    appendLine("_... and ${results.size - 20} more records_")
                }
            }

            if (options.includePrompt) {
                appendLine()
                appendLine("---")
                appendLine()
                appendLine("## Analysis Prompt")
                appendLine()
                append(generateAnalysisPrompt(results))
            }
        }
    }

    private fun appendMarkdownRecord(
        builder: StringBuilder,
        result: ContentScanResult,
        options: ExportOptions
    ) {
        with(builder) {
            val typeLabel = result.fileType?.capitalize() ?: "Unknown"
            appendLine("### Record #${result.metadata.contentId} [$typeLabel]")
            appendLine("- Size: ${formatBytes(result.metadata.size.toLong())}")
            appendLine("- Hash: ${result.metadata.hash.take(12)}...")
            appendLine("- Compressed: ${if (result.metadata.isCompressed) "Yes" else "No"}")

            if (options.includeContent && result.preview != null) {
                appendLine()
                val language = getLanguageForSyntaxHighlight(result.fileType)
                appendLine("```$language")

                val preview = if (result.preview.length > options.maxContentLength) {
                    result.preview.take(options.maxContentLength) + "\n... (truncated)"
                } else {
                    result.preview
                }
                appendLine(preview)
                appendLine("```")
            } else if (result.preview != null) {
                appendLine()
                appendLine("_Preview available (${result.preview.length} chars)_")
            }

            appendLine()
            appendLine("---")
            appendLine()
        }
    }

    private fun exportAsJson(
        results: List<ContentScanResult>,
        options: ExportOptions
    ): String {
        val summary = generateSummary(results)

        return buildString {
            appendLine("{")
            appendLine("  \"summary\": {")
            appendLine("    \"totalRecords\": ${summary.totalRecords},")
            appendLine("    \"textRecords\": ${summary.textRecords},")
            appendLine("    \"binaryRecords\": ${summary.binaryRecords},")
            appendLine("    \"totalSizeBytes\": ${summary.totalSizeBytes},")
            appendLine("    \"fileTypeDistribution\": {")

            val typeEntries = summary.fileTypeDistribution.entries.toList()
            typeEntries.forEachIndexed { index, (type, count) ->
                append("      \"$type\": $count")
                if (index < typeEntries.size - 1) append(",")
                appendLine()
            }

            appendLine("    }")
            appendLine("  },")
            appendLine("  \"records\": [")

            results.forEachIndexed { index, result ->
                appendLine("    {")
                appendLine("      \"contentId\": ${result.metadata.contentId},")
                appendLine("      \"hash\": \"${result.metadata.hash}\",")
                appendLine("      \"size\": ${result.metadata.size},")
                appendLine("      \"isCompressed\": ${result.metadata.isCompressed},")
                appendLine("      \"isText\": ${result.metadata.isText},")
                appendLine("      \"fileType\": ${result.fileType?.let { "\"$it\"" } ?: "null"},")

                if (options.includeContent && result.preview != null) {
                    val escapedPreview = result.preview
                        .take(options.maxContentLength)
                        .replace("\\", "\\\\")
                        .replace("\"", "\\\"")
                        .replace("\n", "\\n")
                        .replace("\r", "\\r")
                        .replace("\t", "\\t")
                    appendLine("      \"preview\": \"$escapedPreview\",")
                }

                append("      \"previewAvailable\": ${result.preview != null}")
                append("    }")
                if (index < results.size - 1) append(",")
                appendLine()
            }

            appendLine("  ]")

            if (options.includePrompt) {
                appendLine(",")
                appendLine("  \"analysisPrompt\": \"${escapeJsonString(generateAnalysisPrompt(results))}\"")
            }

            appendLine("}")
        }
    }

    private fun exportAsCsv(
        results: List<ContentScanResult>,
        options: ExportOptions
    ): String {
        return buildString {
            // CSV header
            append("ContentId,Hash,Size,IsCompressed,IsText,FileType")
            if (options.includeContent) {
                append(",PreviewLength")
            }
            appendLine()

            // CSV records
            results.forEach { result ->
                append("${result.metadata.contentId},")
                append("${result.metadata.hash},")
                append("${result.metadata.size},")
                append("${result.metadata.isCompressed},")
                append("${result.metadata.isText},")
                append("${result.fileType ?: "unknown"}")

                if (options.includeContent) {
                    append(",${result.preview?.length ?: 0}")
                }

                appendLine()
            }

            if (options.includePrompt) {
                appendLine()
                appendLine("# Analysis Prompt:")
                generateAnalysisPrompt(results).lines().forEach { line ->
                    appendLine("# $line")
                }
            }
        }
    }

    private fun analyzeDeletionPatterns(
        results: List<ContentScanResult>,
        deletionEvents: List<DeletionEvent>
    ): String {
        // Group deletions by time periods (e.g., hourly buckets)
        val hourlyBuckets = deletionEvents.groupBy {
            it.timestamp / (1000 * 60 * 60) // Group by hour
        }

        val burstDeletions = hourlyBuckets.filter { it.value.size > 10 }

        // Correlate with content types
        val contentIdToDeletion = deletionEvents.associateBy { it.contentId }
        val deletedContentTypes = results
            .filter { contentIdToDeletion.containsKey(it.metadata.contentId) }
            .groupingBy { it.fileType ?: "unknown" }
            .eachCount()

        return buildString {
            appendLine("### Deletion Timeline")
            appendLine("- Total deletion events: ${deletionEvents.size}")
            appendLine("- Burst deletions detected: ${burstDeletions.size} periods with >10 deletions/hour")

            if (burstDeletions.isNotEmpty()) {
                appendLine()
                appendLine("### Burst Deletion Periods")
                burstDeletions.forEach { (hourBucket, events) ->
                    val timestamp = hourBucket * 1000 * 60 * 60
                    appendLine("- ${DATE_FORMAT.format(Date(timestamp))}: ${events.size} deletions")
                }
            }

            appendLine()
            appendLine("### Deleted Content Types")
            deletedContentTypes.entries
                .sortedByDescending { it.value }
                .forEach { (type, count) ->
                    appendLine("- $type: $count files")
                }

            appendLine()
            appendLine("### Pattern Analysis")

            // Detect refactoring patterns (many files deleted at once)
            if (burstDeletions.any { it.value.size > 20 }) {
                appendLine("- **Possible refactoring detected**: Large batches of files deleted simultaneously")
            }

            // Detect cleanup patterns (specific file types)
            val tempFileTypes = deletedContentTypes.filterKeys {
                it.contains("tmp") || it.contains("temp") || it.contains("backup")
            }
            if (tempFileTypes.isNotEmpty()) {
                appendLine("- **Cleanup operation detected**: Temporary/backup files removed")
            }

            // Detect accidental deletions (isolated high-value files)
            val valuableTypes = setOf("java", "kotlin", "typescript", "javascript", "python")
            val deletedValuableFiles = deletedContentTypes.filterKeys { it in valuableTypes }
            if (deletedValuableFiles.values.sum() < 5 && deletedValuableFiles.isNotEmpty()) {
                appendLine("- **Possible accidental deletion**: Small number of source code files deleted")
            }
        }
    }

    private fun patternAnalysisToJson(analysis: String): String {
        val escapedAnalysis = escapeJsonString(analysis)
        return "\"$escapedAnalysis\""
    }

    private fun formatBytes(bytes: Long): String {
        return when {
            bytes < 1024 -> "$bytes B"
            bytes < 1024 * 1024 -> "%.2f KB".format(bytes / 1024.0)
            bytes < 1024 * 1024 * 1024 -> "%.2f MB".format(bytes / (1024.0 * 1024))
            else -> "%.2f GB".format(bytes / (1024.0 * 1024 * 1024))
        }
    }

    private fun calculatePercentage(part: Int, total: Int): Int {
        return if (total == 0) 0 else (part * 100) / total
    }

    private fun getLanguageForSyntaxHighlight(fileType: String?): String {
        return when (fileType) {
            "java" -> "java"
            "kotlin" -> "kotlin"
            "javascript" -> "javascript"
            "typescript" -> "typescript"
            "python" -> "python"
            "xml" -> "xml"
            "html" -> "html"
            "css" -> "css"
            "sql" -> "sql"
            "json" -> "json"
            "yaml" -> "yaml"
            "markdown" -> "markdown"
            "gradle" -> "gradle"
            "properties" -> "properties"
            else -> ""
        }
    }

    private fun escapeJsonString(str: String): String {
        return str
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
    }
}