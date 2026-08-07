//! Checked-in regression test for cmdcrush's compression pipeline.
//!
//! Unlike `cmdcrush --history-stats` (which scans `~/.claude/projects` and is
//! therefore non-deterministic and machine-dependent), this test runs fixed,
//! checked-in fixtures through the real `cmdcrush` binary and asserts two
//! invariants release-over-release:
//!
//!   1. Never-worse: compressed output is never larger than the input.
//!   2. No silent regression: each fixture still fires the compression method
//!      it's designed to exercise, and still saves at least a minimum
//!      percentage of bytes. If a future change breaks a stage (e.g. it stops
//!      firing, or a bug makes it less effective), one of these fixtures
//!      should catch it.
//!
//! This runs the actual compiled binary (not a reimplementation of its
//! internal logic) so it exercises the exact code path a real invocation
//! takes.

use std::io::Write;
use std::process::Command;

fn cmdcrush() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cmdcrush"))
}

/// Run `cmdcrush -- cat <fixture>` with stats on stderr and no disk
/// archiving (irrelevant to this test and would leave temp files behind).
/// Returns (stdout, stderr).
fn run_fixture(content: &str) -> (String, String) {
    let mut file = tempfile::NamedTempFile::new().expect("create fixture temp file");
    file.write_all(content.as_bytes()).expect("write fixture");
    let path = file.path();

    let out = cmdcrush()
        .args(["--stats", "--floor-bytes", "1", "--no-archive", "--max-lines", "20", "--"])
        .arg("cat")
        .arg(path)
        .output()
        .expect("failed to run cmdcrush");

    assert!(out.status.success(), "cmdcrush exited non-zero: {out:?}");
    (
        String::from_utf8(out.stdout).expect("stdout must be valid UTF-8"),
        String::from_utf8_lossy(&out.stderr).to_string(),
    )
}

/// Asserts the never-worse invariant and that the given method (and minimum
/// savings percentage) shows up in the `--stats` line on stderr.
fn assert_compresses(content: &str, expected_method: &str, min_pct_saved: f64) {
    let (stdout, stderr) = run_fixture(content);

    assert!(
        stdout.len() <= content.len(),
        "never-worse invariant violated: {} bytes in, {} bytes out",
        content.len(),
        stdout.len()
    );

    let stats_line = stderr
        .lines()
        .find(|l| l.contains("via "))
        .unwrap_or_else(|| panic!("no --stats line found on stderr: {stderr:?}"));
    // `+truncated` may be appended on top of the base method, so match by
    // prefix rather than requiring an exact method string.
    assert!(
        stats_line.contains(&format!("via {expected_method}"))
            && stats_line
                .split("via ")
                .nth(1)
                .is_some_and(|m| m.starts_with(expected_method)),
        "expected method `{expected_method}` (optionally +truncated) in stats line, got: {stats_line:?}"
    );

    let pct: f64 = stats_line
        .rsplit('(')
        .next()
        .and_then(|s| s.split('%').next())
        .and_then(|s| s.trim().parse().ok())
        .unwrap_or_else(|| panic!("couldn't parse % saved from stats line: {stats_line:?}"));
    assert!(
        pct >= min_pct_saved,
        "regression: `{expected_method}` fixture only saved {pct:.1}%, expected >= {min_pct_saved:.1}%"
    );
}

#[test]
fn json_array_triggers_smart_crush() {
    // 6 objects sharing 3 constant fields ("level"/"service"/"env") and one
    // varying field ("msg") -- SmartCrusher should hoist the constants.
    let mut arr = Vec::new();
    for i in 0..6 {
        arr.push(format!(
            r#"{{"level":"info","service":"checkout","env":"prod","msg":"processed request {i}"}}"#
        ));
    }
    let json = format!("[{}]", arr.join(","));
    assert_compresses(&json, "json-smart-crush", 10.0);
}

#[test]
fn fenced_code_block_with_comments_triggers_code_compress() {
    let text = format!(
        "Build log:\n\n```rust\n{}\n```\n\nDone.\n",
        (0..30)
            .map(|i| format!(
                "// this is a fairly long explanatory comment on line {i} that exists only to be stripped\nfn step_{i}() {{ do_work({i}); }}"
            ))
            .collect::<Vec<_>>()
            .join("\n")
    );
    assert_compresses(&text, "code-compress", 10.0);
}

#[test]
fn unified_diff_triggers_diff_compaction() {
    let mut diff = String::from("diff --git a/src/lib.rs b/src/lib.rs\n");
    diff.push_str("index 1111111..2222222 100644\n--- a/src/lib.rs\n+++ b/src/lib.rs\n");
    for i in 0..40 {
        diff.push_str(&format!("@@ -{i},3 +{i},3 @@\n context line {i}\n-old line {i}\n+new line {i}\n context line {i}\n"));
    }
    assert_compresses(&diff, "diff", 5.0);
}

#[test]
fn repeated_progress_bar_triggers_text_compress() {
    let mut text = String::new();
    for pct in 0..=100 {
        text.push_str(&format!("\rDownloading... {pct}% [{}]", "#".repeat(pct / 2)));
    }
    text.push_str("\rDownloading... 100% done\n");
    assert_compresses(&text, "text", 50.0);
}

#[test]
fn long_unique_output_triggers_line_truncation() {
    let text: String = (0..500)
        .map(|i| format!("line {i}: unique unrepeated content token-{i}-abcdef\n"))
        .collect();
    let (stdout, stderr) = run_fixture(&text);
    assert!(stdout.len() < text.len(), "expected truncation to shrink output");
    let stats_line = stderr.lines().find(|l| l.contains("via ")).expect("stats line");
    assert!(
        stats_line.contains("truncated"),
        "expected a `+truncated` method, got: {stats_line:?}"
    );
}
