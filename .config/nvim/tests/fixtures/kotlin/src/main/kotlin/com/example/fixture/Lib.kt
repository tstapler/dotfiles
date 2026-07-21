package com.example.fixture

/**
 * Tiny fixture file for exercising cross-file go-to-definition/references
 * under nvim-next's kotlin-language-server setup.
 */

/** Returns a greeting for name — a cross-file gd/grr target. */
fun greet(name: String): String {
    return "Hello, $name!"
}

/**
 * Sums nums — a good breakpoint target if Kotlin DAP is ever wired up: a
 * loop with a local accumulator to inspect mid-loop.
 */
fun total(nums: List<Int>): Int {
    var result = 0
    for (n in nums) {
        result += n
    }
    return result
}
