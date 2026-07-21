package com.example.fixture;

/**
 * Tiny fixture class for exercising cross-file go-to-definition/references
 * and DAP breakpoints under nvim-next's jdtls setup.
 */
public class Lib {

    /** Returns a greeting for name — a cross-file gd/grr target. */
    public static String greet(String name) {
        return "Hello, " + name + "!";
    }

    /**
     * Sums nums — a good DAP breakpoint target: a loop with a local
     * accumulator to set a breakpoint on and inspect mid-loop.
     */
    public static int sum(int[] nums) {
        int total = 0;
        for (int n : nums) {
            total += n;
        }
        return total;
    }
}
