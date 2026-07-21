//! Tiny fixture program: depends on fixture_lib across a Cargo workspace
//! crate boundary so `gd` on greet/sum jumps into ../lib, and the sum()
//! call is a good spot to set a DAP breakpoint via <leader>db.

use fixture_lib::{greet, sum};

fn main() {
    let msg = greet("World");
    println!("{msg}");

    let nums = vec![1, 2, 3, 4, 5];
    let total = sum(&nums);
    println!("Total: {total}");
}
