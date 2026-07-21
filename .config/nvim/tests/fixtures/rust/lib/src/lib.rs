//! Tiny fixture crate for exercising cross-crate go-to-definition/references
//! and DAP breakpoints under nvim-next's rustaceanvim + codelldb setup.

/// Returns a greeting for `name` — a cross-crate gd/grr target.
pub fn greet(name: &str) -> String {
    format!("Hello, {name}!")
}

/// Sums `nums` — a good DAP breakpoint target: a loop with a local
/// accumulator to set a breakpoint on and inspect mid-loop.
pub fn sum(nums: &[i32]) -> i32 {
    let mut total = 0;
    for n in nums {
        total += n;
    }
    total
}
