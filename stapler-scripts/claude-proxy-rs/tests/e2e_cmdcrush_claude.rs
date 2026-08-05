/// On-demand end-to-end tests: cmdcrush wrapping a real `claude` CLI
/// invocation, so compression is exercised against genuine model output
/// instead of synthetic fixtures.
///
/// These hit the network, need `claude` auth, and cost tokens, so they're
/// `#[ignore]`d by default. Run explicitly with:
///   cargo test --test e2e_cmdcrush_claude -- --ignored --nocapture
use std::process::{Command, Stdio};

// `claude --model` resolves family aliases ("haiku", "sonnet", "opus", "fable")
// to that family's latest model itself -- no need to pin/resolve/cache an ID here.
const MODEL: &str = "haiku";

fn cmdcrush() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cmdcrush"))
}

fn require_claude_on_path() {
    let found = Command::new("claude")
        .arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false);
    assert!(found, "`claude` CLI not found on PATH — required for this e2e test");
}

#[test]
#[ignore]
fn text_output_from_real_claude_round_trips() {
    require_claude_on_path();

    let out = cmdcrush()
        .args([
            "--stats",
            "--floor-bytes",
            "1",
            "--",
            "claude",
            "-p",
            "Reply with exactly the word: pong",
            "--model",
            MODEL,
        ])
        .output()
        .expect("failed to run cmdcrush");

    assert!(out.status.success(), "cmdcrush/claude exited non-zero: {out:?}");
    let stdout = String::from_utf8(out.stdout).expect("cmdcrush stdout must be valid UTF-8");
    assert!(
        stdout.to_lowercase().contains("pong"),
        "expected 'pong' in output, got: {stdout:?}"
    );

    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        stderr.contains("cmdcrush:"),
        "expected --stats diagnostics on stderr, got: {stderr:?}"
    );
}

#[test]
#[ignore]
fn json_output_from_real_claude_stays_valid_json() {
    require_claude_on_path();

    let out = cmdcrush()
        .args([
            "--stats",
            "--floor-bytes",
            "1",
            "--",
            "claude",
            "-p",
            "Reply with exactly: pong",
            "--model",
            MODEL,
            "--output-format",
            "json",
        ])
        .output()
        .expect("failed to run cmdcrush");

    assert!(out.status.success(), "cmdcrush/claude exited non-zero: {out:?}");
    let stdout = String::from_utf8(out.stdout).expect("cmdcrush stdout must be valid UTF-8");

    let parsed: serde_json::Value = serde_json::from_str(&stdout)
        .unwrap_or_else(|e| panic!("cmdcrush output is not valid JSON ({e}): {stdout:?}"));
    assert!(parsed.is_object(), "expected a JSON object, got: {parsed:?}");
}
