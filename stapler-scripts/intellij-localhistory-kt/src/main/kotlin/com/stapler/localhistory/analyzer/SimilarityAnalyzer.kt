package com.stapler.localhistory.analyzer

import com.stapler.localhistory.scanner.ContentScanResult
import kotlin.math.min

/**
 * Represents a group of similar content items
 */
data class SimilarityGroup(
    val id: Int,
    val members: List<ContentScanResult>,
    val representativeId: Int,  // Content ID of the most representative member
    val averageSimilarity: Float,
    val fileType: String?
) {
    val size: Int get() = members.size
    val totalSize: Long get() = members.sumOf { it.metadata.size.toLong() }
}

/**
 * Result of similarity analysis
 */
data class SimilarityAnalysisResult(
    val groups: List<SimilarityGroup>,
    val duplicates: List<Pair<Int, Int>>,  // Pairs of content IDs that are exact duplicates
    val totalAnalyzed: Int,
    val groupedCount: Int,
    val ungroupedCount: Int
) {
    val duplicateCount: Int get() = duplicates.size
    val groupCount: Int get() = groups.size
}

/**
 * Configuration for similarity analysis
 */
data class SimilarityConfig(
    val similarityThreshold: Float = 0.7f,  // Minimum similarity to consider items related
    val duplicateThreshold: Float = 0.95f,  // Threshold for considering items duplicates
    val maxGroupSize: Int = 100,  // Maximum items per group
    val minGroupSize: Int = 2,    // Minimum items to form a group
    val useSimHash: Boolean = true,  // Use SimHash for initial screening
    val maxComparisons: Int = 10000  // Maximum pairwise comparisons to perform
)

/**
 * Analyzes content similarity to identify related and duplicate content
 *
 * Uses a combination of techniques:
 * 1. SimHash for fast initial screening (locality-sensitive hashing)
 * 2. Token-based Jaccard similarity for detailed comparison
 * 3. Union-Find for efficient clustering
 */
class SimilarityAnalyzer(
    private val classifier: ContentClassifier = ContentClassifier()
) {

    companion object {
        // Number of bits to consider for SimHash similarity (Hamming distance threshold)
        private const val SIMHASH_DISTANCE_THRESHOLD = 8
        private const val TOKEN_MIN_LENGTH = 3
    }

    /**
     * Analyze similarity across a list of content scan results
     *
     * @param results List of content scan results to analyze
     * @param config Configuration for similarity analysis
     * @return Analysis result with groups and duplicates
     */
    fun analyze(
        results: List<ContentScanResult>,
        config: SimilarityConfig = SimilarityConfig()
    ): SimilarityAnalysisResult {
        if (results.isEmpty()) {
            return SimilarityAnalysisResult(
                groups = emptyList(),
                duplicates = emptyList(),
                totalAnalyzed = 0,
                groupedCount = 0,
                ungroupedCount = 0
            )
        }

        // Filter to text content only for meaningful similarity analysis
        val textResults = results.filter { it.metadata.isText && it.preview != null }

        if (textResults.isEmpty()) {
            return SimilarityAnalysisResult(
                groups = emptyList(),
                duplicates = emptyList(),
                totalAnalyzed = results.size,
                groupedCount = 0,
                ungroupedCount = results.size
            )
        }

        // Calculate SimHash for each item
        val simHashes = textResults.associate { result ->
            result.metadata.contentId to calculateSimHash(result.preview ?: "")
        }

        // Find candidate pairs using SimHash (fast screening)
        val candidatePairs = if (config.useSimHash) {
            findCandidatePairsBySimHash(textResults, simHashes, config)
        } else {
            generateAllPairs(textResults, config.maxComparisons)
        }

        // Calculate detailed similarity for candidate pairs
        val similarities = mutableMapOf<Pair<Int, Int>, Float>()
        val duplicates = mutableListOf<Pair<Int, Int>>()

        for ((id1, id2) in candidatePairs) {
            val result1 = textResults.find { it.metadata.contentId == id1 } ?: continue
            val result2 = textResults.find { it.metadata.contentId == id2 } ?: continue

            val similarity = calculateJaccardSimilarity(
                result1.preview ?: "",
                result2.preview ?: ""
            )

            if (similarity >= config.similarityThreshold) {
                val key = if (id1 < id2) id1 to id2 else id2 to id1
                similarities[key] = similarity

                if (similarity >= config.duplicateThreshold) {
                    duplicates.add(key)
                }
            }
        }

        // Cluster similar items using Union-Find
        val groups = clusterSimilarItems(textResults, similarities, config)

        val groupedCount = groups.sumOf { it.size }

        return SimilarityAnalysisResult(
            groups = groups,
            duplicates = duplicates,
            totalAnalyzed = results.size,
            groupedCount = groupedCount,
            ungroupedCount = results.size - groupedCount
        )
    }

    /**
     * Find duplicate content (exact or near-exact matches)
     */
    fun findDuplicates(
        results: List<ContentScanResult>,
        threshold: Float = 0.95f
    ): List<Pair<Int, Int>> {
        val config = SimilarityConfig(
            similarityThreshold = threshold,
            duplicateThreshold = threshold
        )
        val analysisResult = analyze(results, config)
        return analysisResult.duplicates
    }

    /**
     * Group related content by similarity
     */
    fun groupRelatedContent(
        results: List<ContentScanResult>,
        threshold: Float = 0.7f
    ): List<SimilarityGroup> {
        val config = SimilarityConfig(similarityThreshold = threshold)
        val analysisResult = analyze(results, config)
        return analysisResult.groups
    }

    /**
     * Find content similar to a specific item
     */
    fun findSimilarTo(
        targetResult: ContentScanResult,
        allResults: List<ContentScanResult>,
        threshold: Float = 0.6f,
        maxResults: Int = 10
    ): List<Pair<ContentScanResult, Float>> {
        if (targetResult.preview == null || !targetResult.metadata.isText) {
            return emptyList()
        }

        val targetTokens = tokenize(targetResult.preview)
        val similarities = mutableListOf<Pair<ContentScanResult, Float>>()

        for (result in allResults) {
            if (result.metadata.contentId == targetResult.metadata.contentId) continue
            if (result.preview == null || !result.metadata.isText) continue

            val similarity = calculateJaccardSimilarity(targetTokens, tokenize(result.preview))
            if (similarity >= threshold) {
                similarities.add(result to similarity)
            }
        }

        return similarities
            .sortedByDescending { it.second }
            .take(maxResults)
    }

    // Private helper methods

    /**
     * Calculate SimHash for text content
     * SimHash is a locality-sensitive hash that produces similar hashes for similar content
     */
    private fun calculateSimHash(text: String): Long {
        val tokens = tokenize(text)
        if (tokens.isEmpty()) return 0L

        // Initialize feature vector
        val vectorSize = 64
        val vector = IntArray(vectorSize)

        // Calculate weighted feature vector
        for (token in tokens) {
            val hash = token.hashCode()
            for (i in 0 until vectorSize) {
                if ((hash and (1 shl i)) != 0) {
                    vector[i]++
                } else {
                    vector[i]--
                }
            }
        }

        // Generate final hash
        var simHash = 0L
        for (i in 0 until vectorSize) {
            if (vector[i] > 0) {
                simHash = simHash or (1L shl i)
            }
        }

        return simHash
    }

    /**
     * Calculate Hamming distance between two SimHashes
     */
    private fun hammingDistance(hash1: Long, hash2: Long): Int {
        val xor = hash1 xor hash2
        return java.lang.Long.bitCount(xor)
    }

    /**
     * Find candidate pairs using SimHash locality-sensitive hashing
     */
    private fun findCandidatePairsBySimHash(
        results: List<ContentScanResult>,
        simHashes: Map<Int, Long>,
        config: SimilarityConfig
    ): List<Pair<Int, Int>> {
        val candidates = mutableListOf<Pair<Int, Int>>()
        val ids = results.map { it.metadata.contentId }

        var comparisons = 0
        for (i in ids.indices) {
            if (comparisons >= config.maxComparisons) break

            for (j in i + 1 until ids.size) {
                if (comparisons >= config.maxComparisons) break

                val hash1 = simHashes[ids[i]] ?: continue
                val hash2 = simHashes[ids[j]] ?: continue

                val distance = hammingDistance(hash1, hash2)
                if (distance <= SIMHASH_DISTANCE_THRESHOLD) {
                    candidates.add(ids[i] to ids[j])
                }
                comparisons++
            }
        }

        return candidates
    }

    /**
     * Generate all pairs for comparison (fallback when SimHash is disabled)
     */
    private fun generateAllPairs(
        results: List<ContentScanResult>,
        maxComparisons: Int
    ): List<Pair<Int, Int>> {
        val pairs = mutableListOf<Pair<Int, Int>>()
        val ids = results.map { it.metadata.contentId }

        var count = 0
        for (i in ids.indices) {
            for (j in i + 1 until ids.size) {
                if (count >= maxComparisons) return pairs
                pairs.add(ids[i] to ids[j])
                count++
            }
        }

        return pairs
    }

    /**
     * Calculate Jaccard similarity between two texts
     */
    private fun calculateJaccardSimilarity(text1: String, text2: String): Float {
        val tokens1 = tokenize(text1)
        val tokens2 = tokenize(text2)
        return calculateJaccardSimilarity(tokens1, tokens2)
    }

    private fun calculateJaccardSimilarity(tokens1: Set<String>, tokens2: Set<String>): Float {
        if (tokens1.isEmpty() && tokens2.isEmpty()) return 1f
        if (tokens1.isEmpty() || tokens2.isEmpty()) return 0f

        val intersection = tokens1.intersect(tokens2).size
        val union = tokens1.union(tokens2).size

        return if (union == 0) 0f else intersection.toFloat() / union
    }

    /**
     * Tokenize text into a set of normalized tokens
     */
    private fun tokenize(text: String): Set<String> {
        return text
            .lowercase()
            .split(Regex("[\\s\\p{Punct}]+"))
            .filter { it.length >= TOKEN_MIN_LENGTH }
            .toSet()
    }

    /**
     * Cluster similar items using Union-Find algorithm
     */
    private fun clusterSimilarItems(
        results: List<ContentScanResult>,
        similarities: Map<Pair<Int, Int>, Float>,
        config: SimilarityConfig
    ): List<SimilarityGroup> {
        // Create Union-Find structure
        val parent = mutableMapOf<Int, Int>()
        val rank = mutableMapOf<Int, Int>()

        fun find(x: Int): Int {
            if (parent[x] != x) {
                parent[x] = find(parent[x]!!)
            }
            return parent[x]!!
        }

        fun union(x: Int, y: Int) {
            val px = find(x)
            val py = find(y)
            if (px != py) {
                val rx = rank.getOrDefault(px, 0)
                val ry = rank.getOrDefault(py, 0)
                when {
                    rx < ry -> parent[px] = py
                    rx > ry -> parent[py] = px
                    else -> {
                        parent[py] = px
                        rank[px] = rx + 1
                    }
                }
            }
        }

        // Initialize each item as its own parent
        for (result in results) {
            val id = result.metadata.contentId
            parent[id] = id
            rank[id] = 0
        }

        // Union similar items
        for ((pair, _) in similarities) {
            union(pair.first, pair.second)
        }

        // Group by root parent
        val clusters = mutableMapOf<Int, MutableList<ContentScanResult>>()
        for (result in results) {
            val id = result.metadata.contentId
            val root = find(id)
            clusters.computeIfAbsent(root) { mutableListOf() }.add(result)
        }

        // Filter by minimum group size and create SimilarityGroup objects
        var groupId = 0
        return clusters.values
            .filter { it.size >= config.minGroupSize && it.size <= config.maxGroupSize }
            .map { members ->
                // Calculate average similarity within group
                val memberIds = members.map { it.metadata.contentId }
                val groupSimilarities = similarities.filter { (pair, _) ->
                    pair.first in memberIds && pair.second in memberIds
                }
                val avgSimilarity = if (groupSimilarities.isNotEmpty()) {
                    groupSimilarities.values.average().toFloat()
                } else {
                    1.0f  // Single item groups have 100% self-similarity
                }

                // Find representative (largest content)
                val representative = members.maxByOrNull { it.metadata.size }!!

                // Determine common file type
                val fileTypeCounts = members.groupingBy { it.fileType }.eachCount()
                val dominantType = fileTypeCounts.maxByOrNull { it.value }?.key

                SimilarityGroup(
                    id = groupId++,
                    members = members,
                    representativeId = representative.metadata.contentId,
                    averageSimilarity = avgSimilarity,
                    fileType = dominantType
                )
            }
            .sortedByDescending { it.size }
    }

    /**
     * Calculate similarity matrix for a set of results (for visualization/debugging)
     */
    fun calculateSimilarityMatrix(
        results: List<ContentScanResult>
    ): Map<Pair<Int, Int>, Float> {
        val matrix = mutableMapOf<Pair<Int, Int>, Float>()
        val textResults = results.filter { it.metadata.isText && it.preview != null }

        for (i in textResults.indices) {
            for (j in i until textResults.size) {
                val id1 = textResults[i].metadata.contentId
                val id2 = textResults[j].metadata.contentId

                val similarity = if (i == j) {
                    1.0f
                } else {
                    calculateJaccardSimilarity(
                        textResults[i].preview ?: "",
                        textResults[j].preview ?: ""
                    )
                }

                matrix[id1 to id2] = similarity
                matrix[id2 to id1] = similarity
            }
        }

        return matrix
    }
}
