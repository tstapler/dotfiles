package com.example.fixture

/**
 * Tiny fixture entry point: calls Lib.kt across a file boundary so gd/grr
 * on greet/total exercise cross-file navigation.
 */
fun main() {
    val msg = greet("World")
    println(msg)

    val nums = listOf(1, 2, 3, 4, 5)
    val result = total(nums)
    println("Total: $result")
}
