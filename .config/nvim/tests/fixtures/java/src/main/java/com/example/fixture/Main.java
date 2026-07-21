package com.example.fixture;

/**
 * Tiny fixture entry point: calls Lib across a file boundary so gd/grr on
 * greet/sum exercise cross-file navigation, and the sum() call is a good
 * spot to set a DAP breakpoint via <leader>db.
 */
public class Main {
    public static void main(String[] args) {
        String msg = Lib.greet("World");
        System.out.println(msg);

        int[] nums = {1, 2, 3, 4, 5};
        int total = Lib.sum(nums);
        System.out.println("Total: " + total);
    }
}
