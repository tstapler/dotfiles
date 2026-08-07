/// On-demand end-to-end tests: run a fixture through cmdcrush's compression
/// pipeline, then ask a real `claude` CLI invocation to act as a judge --
/// comparing the original and compressed versions and rating whether any
/// information was lost. This is a fuzzier signal than the byte-count
/// assertions in `compression_regression.rs`; it's meant to catch cases where
/// compression is *technically* lossless-in-spirit but a human (or model)
/// reader would actually miss something -- a fact, a value, an error detail.
///
/// These hit the network, need `claude` auth, and cost tokens, so they're
/// `#[ignore]`d by default and print the judge's full reasoning with
/// `--nocapture` for manual review. Run explicitly with:
///   cargo test --test e2e_fidelity_judge -- --ignored --nocapture
use std::io::Write;
use std::process::{Command, Stdio};

// `claude --model` resolves family aliases ("haiku", "sonnet", "opus", "fable")
// to that family's latest model itself -- no need to pin/resolve/cache an ID here.
const MODEL: &str = "sonnet";

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
    assert!(found, "`claude` CLI not found on PATH -- required for this e2e test");
}

/// Compress `content` via the real cmdcrush binary (`cat <tmpfile>` wrapped)
/// and return the compressed stdout.
fn compress_via_cmdcrush(content: &str) -> String {
    let mut file = tempfile::NamedTempFile::new().expect("create fixture temp file");
    file.write_all(content.as_bytes()).expect("write fixture");

    let out = cmdcrush()
        .args(["--floor-bytes", "1", "--no-archive", "--max-lines", "60", "--"])
        .arg("cat")
        .arg(file.path())
        .output()
        .expect("failed to run cmdcrush");
    assert!(out.status.success(), "cmdcrush exited non-zero: {out:?}");
    String::from_utf8(out.stdout).expect("cmdcrush stdout must be valid UTF-8")
}

/// Ask `claude` to compare original vs. compressed text and return a
/// fidelity verdict as JSON: `{"score": 1-10, "lost_details": [...]}`.
fn judge_fidelity(label: &str, original: &str, compressed: &str) -> serde_json::Value {
    let prompt = format!(
        "You are auditing a lossy text-compression pipeline used to shrink tool \
         output before it's shown to an LLM. Below is the ORIGINAL text and the \
         COMPRESSED text produced from it. Judge whether the compressed version \
         preserves every fact, value, error, and detail a reader would need -- \
         formatting/whitespace changes and de-duplication of exact repeats don't \
         count as loss.\n\n\
         Respond with ONLY a single JSON object, no prose, no markdown fences: \
         {{\"score\": <integer 1-10, 10 = no meaningful information lost>, \
         \"lost_details\": [<short strings describing anything present in \
         ORIGINAL but missing or altered in COMPRESSED; empty array if none>]}}\n\n\
         ORIGINAL:\n{original}\n\n\
         COMPRESSED:\n{compressed}"
    );

    let out = Command::new("claude")
        .args(["-p", &prompt, "--model", MODEL])
        .output()
        .unwrap_or_else(|e| panic!("failed to run claude for `{label}`: {e}"));
    assert!(out.status.success(), "claude exited non-zero for `{label}`: {out:?}");

    let stdout = String::from_utf8_lossy(&out.stdout);
    let json_str = stdout
        .find('{')
        .zip(stdout.rfind('}'))
        .map(|(start, end)| &stdout[start..=end])
        .unwrap_or_else(|| panic!("no JSON object found in judge response for `{label}`: {stdout:?}"));

    serde_json::from_str(json_str)
        .unwrap_or_else(|e| panic!("judge response for `{label}` wasn't valid JSON ({e}): {json_str:?}"))
}

/// Run one fixture end to end: compress, judge, print the verdict, and fail
/// if the judge reports a score below `min_score` (a human should read the
/// printed `lost_details` either way -- the threshold just catches egregious
/// regressions automatically).
fn run_fidelity_case(label: &str, original: &str, min_score: i64) {
    require_claude_on_path();

    let compressed = compress_via_cmdcrush(original);
    println!(
        "\n=== {label}: {} -> {} bytes ({:.1}% saved) ===",
        original.len(),
        compressed.len(),
        100.0 * (1.0 - compressed.len() as f64 / original.len() as f64)
    );

    let verdict = judge_fidelity(label, original, &compressed);
    println!("judge verdict: {verdict}");

    let score = verdict.get("score").and_then(|v| v.as_i64()).unwrap_or_else(|| {
        panic!("judge verdict for `{label}` missing integer `score`: {verdict}")
    });
    let lost: Vec<String> = verdict
        .get("lost_details")
        .and_then(|v| v.as_array())
        .map(|a| a.iter().filter_map(|v| v.as_str().map(str::to_string)).collect())
        .unwrap_or_default();
    if !lost.is_empty() {
        println!("lost details reported by judge for `{label}`:");
        for detail in &lost {
            println!("  - {detail}");
        }
    }

    assert!(
        score >= min_score,
        "`{label}` scored {score}/10 for fidelity (want >= {min_score}); lost_details: {lost:?}"
    );
}

#[test]
#[ignore]
fn json_smart_crush_preserves_all_field_values() {
    let mut entries = Vec::new();
    for i in 0..8 {
        entries.push(format!(
            r#"{{"level":"error","service":"payments","region":"us-east-1","request_id":"req-{i}","message":"card declined for order {i}: insufficient funds"}}"#
        ));
    }
    let original = format!("[{}]", entries.join(","));
    run_fidelity_case("json_smart_crush", &original, 8);
}

#[test]
#[ignore]
fn code_comment_stripping_preserves_logic_but_may_lose_rationale() {
    let original = "```rust\n\
        // Retry with exponential backoff because the upstream API rate-limits\n\
        // aggressively above 50 req/s -- see incident INC-4821 for context.\n\
        fn call_with_retry(n: u32) -> Result<Response, Error> {\n\
        \x20   for attempt in 0..n {\n\
        \x20       // Sleep grows 2^attempt seconds, capped at 30s\n\
        \x20       if let Ok(r) = call() { return Ok(r); }\n\
        \x20       std::thread::sleep(backoff(attempt));\n\
        \x20   }\n\
        \x20   Err(Error::RetriesExhausted)\n\
        }\n\
        ```\n";
    // Comment stripping is *expected* to drop the incident reference and the
    // backoff-formula explanation -- this case is about confirming the judge
    // actually notices and reports that loss, not about it scoring high.
    run_fidelity_case("code_comment_stripping", original, 1);
}

#[test]
#[ignore]
fn diff_compaction_preserves_every_hunk_change() {
    let mut diff = String::from("diff --git a/config.yaml b/config.yaml\n");
    diff.push_str("index 1111111..2222222 100644\n--- a/config.yaml\n+++ b/config.yaml\n");
    diff.push_str("@@ -1,5 +1,5 @@\n timeout: 30\n-retries: 3\n+retries: 5\n backoff: exponential\n");
    diff.push_str("@@ -10,3 +10,3 @@\n region: us-east-1\n-max_connections: 100\n+max_connections: 250\n pool: shared\n");
    run_fidelity_case("diff_compaction", &diff, 8);
}
