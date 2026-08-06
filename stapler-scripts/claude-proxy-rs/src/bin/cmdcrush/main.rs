//! cmdcrush — run a command and compress its captured output before it
//! reaches an LLM context (an in-house, trust-boundary-controlled alternative
//! to wrapping shell output with a third-party CLI proxy).
//!
//! Reuses `claude_proxy_rs::compression::TextCompressor`, the same native
//! text compressor the main proxy applies to assistant/log-like message
//! content at the `/v1/messages` boundary.
//!
//! Stdout and stderr are captured concurrently (not sequentially via
//! `Command::output()`, which discards arrival order) so that when a command
//! writes to both streams, the interleaving between them survives: if both
//! streams produced output, they're merged into a single ordered stream on
//! stdout with stderr lines tagged `[stderr]`. If only one stream produced
//! output (the common case), it is compressed and printed to its own fd
//! exactly as before.

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command as Proc, Stdio};
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

use clap::Parser;
use opentelemetry::metrics::{Counter, Histogram, MeterProvider as _};
use opentelemetry::KeyValue;
use opentelemetry_sdk::metrics::{PeriodicReader, SdkMeterProvider};
use serde_json::Value;
use sha2::{Digest, Sha256};

use claude_proxy_rs::compression::{
    collapse_common_prefix, compact_diff, is_diff, truncate_lines, TextCompressor,
};

mod metrics_store;
use metrics_store::SqliteMetricsExporter;

#[derive(Parser)]
#[command(
    name = "cmdcrush",
    about = "Run a command and compress its output before printing it."
)]
struct Cli {
    /// Print before/after byte counts to stderr.
    #[arg(long)]
    stats: bool,

    /// Below this combined byte size, output is passed through unchanged.
    #[arg(long, default_value_t = 1000)]
    floor_bytes: usize,

    /// Skip archiving the original (uncompressed) output for later retrieval.
    #[arg(long)]
    no_archive: bool,

    /// Directory to archive originals into (default: a temp dir).
    #[arg(long)]
    archive_dir: Option<PathBuf>,

    /// After other compression, cap output to this many lines total (head +
    /// tail), eliding the middle. 0 disables truncation.
    #[arg(long, default_value_t = 400)]
    max_lines: usize,

    /// Instead of running a command, scan existing Claude Code conversation
    /// transcripts and report how many bytes the compression pipeline would
    /// have saved on their recorded tool outputs, had it been run inline.
    #[arg(long)]
    history_stats: bool,

    /// Root directory to scan for `*.jsonl` transcripts (used only with
    /// `--history-stats`). Defaults to `~/.claude/projects`.
    #[arg(long)]
    history_dir: Option<PathBuf>,

    /// Number of largest individual savings to list in the `--history-stats`
    /// report.
    #[arg(long, default_value_t = 10)]
    top: usize,

    /// Command (and its arguments) to run.
    #[arg(trailing_var_arg = true, num_args = 0..)]
    command: Vec<String>,
}

enum Chunk {
    Stdout(Vec<u8>),
    Stderr(Vec<u8>),
}

/// Read `r` line-by-line (on the raw `\n` byte, which is unambiguous even
/// inside binary data or multi-byte UTF-8 — 0x0A never occurs as a
/// continuation byte) and forward each line to `tx`, tagged via `wrap`.
fn spawn_reader<R: Read + Send + 'static>(
    r: R,
    wrap: fn(Vec<u8>) -> Chunk,
    tx: mpsc::Sender<Chunk>,
) -> thread::JoinHandle<()> {
    thread::spawn(move || {
        let mut reader = BufReader::new(r);
        loop {
            let mut line = Vec::new();
            match reader.read_until(b'\n', &mut line) {
                Ok(0) | Err(_) => break,
                Ok(_) => {
                    if tx.send(wrap(line)).is_err() {
                        break;
                    }
                }
            }
        }
    })
}

/// Route `text` through the compressor(s) suited to its shape, then apply a
/// final head/tail cap. Content routing mirrors headroom's "SmartCrusher"
/// idea (dispatch by detected content type rather than one generic pass over
/// everything): JSON gets minified verbatim, unified diffs get hunk-aware
/// compaction, path-heavy output gets its common directory prefix collapsed,
/// and everything else gets the general-purpose `TextCompressor`. Every
/// stage is a no-op (returns its input unchanged) when it wouldn't shrink
/// the text, so composing them can only ever reduce size.
fn compress_text(text: &str, max_lines: usize) -> (String, String) {
    if let Ok(value) = serde_json::from_str::<serde_json::Value>(text.trim()) {
        if let Ok(minified) = serde_json::to_string(&value) {
            if minified.len() < text.len() {
                return (minified, "json-minify".to_string());
            }
        }
        return (text.to_string(), "json-noop".to_string());
    }

    let (mut compressed, mut method) = if is_diff(text) {
        (compact_diff(text), "diff".to_string())
    } else {
        (TextCompressor::new().compress(text), "text".to_string())
    };

    if !is_diff(text) {
        let collapsed = collapse_common_prefix(&compressed);
        if collapsed.len() < compressed.len() {
            compressed = collapsed;
            method = "path-collapse".to_string();
        }
    }

    if max_lines > 0 {
        let head = max_lines / 2;
        let tail = max_lines - head;
        let truncated = truncate_lines(&compressed, head, tail);
        if truncated.len() < compressed.len() {
            compressed = truncated;
            method = format!("{method}+truncated");
        }
    }

    (compressed, method)
}

/// The metrics `command` attribute should name the tool the user actually
/// ran, not the shell that ran it — the hook always wraps the real command
/// as `bash -c '<real command>'` (see `~/.claude/hooks/cmdcrush-wrap.sh`), so
/// `program` here is unconditionally `"bash"` and would make every row in
/// the stats DB indistinguishable by command otherwise.
fn command_label(program: &str, args: &[String]) -> String {
    let is_shell = matches!(program, "bash" | "sh" | "zsh" | "dash");
    if is_shell {
        if let Some(pos) = args.iter().position(|a| a == "-c") {
            if let Some(script) = args.get(pos + 1) {
                return first_word(script);
            }
        }
    }
    program.to_string()
}

/// First real command token in a shell script fragment: skips leading
/// `FOO=bar` env assignments and a leading `sudo`.
fn first_word(script: &str) -> String {
    let mut tokens = script.split_whitespace();
    let mut word = tokens.next().unwrap_or("");
    while !word.is_empty() && word.contains('=') && !word.starts_with('-') {
        word = tokens.next().unwrap_or("");
    }
    if word == "sudo" {
        word = tokens.next().unwrap_or("sudo");
    }
    if word.is_empty() {
        "unknown".to_string()
    } else {
        word.to_string()
    }
}

/// One tool-output blob pulled out of a transcript, plus what compressing it
/// would have done.
struct HistoryEntry {
    source: String,
    before: usize,
    after: usize,
    method: String,
}

/// Pull the text of every `tool_result` block out of a single JSONL
/// transcript line, if that line is a `user` message carrying tool results.
/// Claude Code stores `content` either as a bare string or as a list of
/// content blocks (`{"type": "tool_result", "content": ...}` where the inner
/// `content` is itself a string or a list of `{"type": "text", "text": ...}`
/// blocks) — both shapes are handled.
fn extract_tool_results(line: &str) -> Vec<String> {
    let Ok(value) = serde_json::from_str::<Value>(line) else {
        return Vec::new();
    };
    if value.get("type").and_then(Value::as_str) != Some("user") {
        return Vec::new();
    }
    let Some(content) = value.pointer("/message/content") else {
        return Vec::new();
    };
    let Some(blocks) = content.as_array() else {
        return Vec::new();
    };

    blocks
        .iter()
        .filter(|b| b.get("type").and_then(Value::as_str) == Some("tool_result"))
        .filter_map(|b| b.get("content"))
        .filter_map(tool_result_text)
        .collect()
}

/// Flatten a `tool_result` block's `content` field (string, or list of
/// `{"type": "text", "text": ...}` blocks) into plain text.
fn tool_result_text(content: &Value) -> Option<String> {
    if let Some(s) = content.as_str() {
        return Some(s.to_string());
    }
    let blocks = content.as_array()?;
    let text: String = blocks
        .iter()
        .filter(|b| b.get("type").and_then(Value::as_str) == Some("text"))
        .filter_map(|b| b.get("text").and_then(Value::as_str))
        .collect::<Vec<_>>()
        .join("\n");
    if text.is_empty() {
        None
    } else {
        Some(text)
    }
}

/// Scan every `*.jsonl` transcript under `dir`, run each recorded tool
/// output through the same `compress_text` pipeline `cmdcrush` applies live,
/// and report the aggregate savings. Never modifies anything it reads.
fn run_history_stats(dir: &Path, floor_bytes: usize, max_lines: usize, top_n: usize) {
    let pattern = format!("{}/**/*.jsonl", dir.display());
    let paths: Vec<PathBuf> = match glob::glob(&pattern) {
        Ok(g) => g.filter_map(Result::ok).collect(),
        Err(e) => {
            eprintln!("cmdcrush: invalid history dir pattern {pattern}: {e}");
            std::process::exit(1);
        }
    };

    if paths.is_empty() {
        eprintln!("cmdcrush: no transcripts found under {}", dir.display());
        std::process::exit(1);
    }

    let mut total_before: u64 = 0;
    let mut total_after: u64 = 0;
    let mut blob_count: u64 = 0;
    // method -> (before, after, count)
    let mut by_method: HashMap<String, (u64, u64, u64)> = HashMap::new();
    let mut top_savings: Vec<HistoryEntry> = Vec::new();

    for path in &paths {
        let Ok(file) = std::fs::File::open(path) else {
            continue;
        };
        let reader = BufReader::new(file);
        for (lineno, line) in reader.lines().enumerate() {
            let Ok(line) = line else { continue };
            for text in extract_tool_results(&line) {
                blob_count += 1;
                let before = text.len();
                let (after, method) = if before < floor_bytes {
                    (before, "below-floor".to_string())
                } else {
                    let (compressed, method) = compress_text(&text, max_lines);
                    (compressed.len(), method)
                };

                total_before += before as u64;
                total_after += after as u64;
                let entry = by_method.entry(method.clone()).or_insert((0, 0, 0));
                entry.0 += before as u64;
                entry.1 += after as u64;
                entry.2 += 1;

                if before > after {
                    top_savings.push(HistoryEntry {
                        source: format!("{}:{}", path.display(), lineno + 1),
                        before,
                        after,
                        method,
                    });
                }
            }
        }
    }

    top_savings.sort_by_key(|e| std::cmp::Reverse(e.before - e.after));
    top_savings.truncate(top_n);

    let pct = if total_before == 0 {
        0.0
    } else {
        100.0 * (1.0 - total_after as f64 / total_before as f64)
    };
    let tokens_saved = (total_before.saturating_sub(total_after)) as f64 / 4.0;

    println!("cmdcrush history-stats — scanned {} transcript(s) under {}", paths.len(), dir.display());
    println!("tool-output blobs examined: {blob_count}");
    println!(
        "bytes: {total_before} -> {total_after} ({pct:.1}% saved, ~{tokens_saved:.0} tokens at 4 bytes/token)"
    );
    println!();
    println!("by method:");
    let mut methods: Vec<_> = by_method.into_iter().collect();
    methods.sort_by_key(|(_, (before, after, _))| std::cmp::Reverse(before.saturating_sub(*after)));
    for (method, (before, after, count)) in methods {
        let mpct = if before == 0 {
            0.0
        } else {
            100.0 * (1.0 - after as f64 / before as f64)
        };
        println!("  {method:<20} {count:>6} blobs   {before:>10} -> {after:>10} bytes  ({mpct:.1}% saved)");
    }

    if !top_savings.is_empty() {
        println!();
        println!("top {} individual savings:", top_savings.len());
        for e in &top_savings {
            let saved = e.before - e.after;
            println!("  {saved:>8} bytes saved  [{}]  {}", e.method, e.source);
        }
    }
}

/// Persist the original bytes so a human can retrieve them later, keyed by
/// a short sha256 prefix. Returns the archive path on success.
fn archive_original(bytes: &[u8], dir: &Path) -> std::io::Result<PathBuf> {
    std::fs::create_dir_all(dir)?;
    let digest = Sha256::digest(bytes);
    let hash = hex::encode(&digest[..8]);
    let path = dir.join(format!("{hash}.orig"));
    std::fs::write(&path, bytes)?;
    Ok(path)
}

/// OTel metrics pipeline that persists to `metrics_store`'s SQLite exporter
/// instead of a network collector — cmdcrush is a one-shot CLI with no
/// collector to talk to. Always built; `--stats` only controls the extra
/// stderr diagnostic line in `print_result`.
struct Metrics {
    provider: SdkMeterProvider,
    invocations: Counter<u64>,
    bytes_before: Histogram<u64>,
    bytes_after: Histogram<u64>,
}

fn init_metrics() -> Option<Metrics> {
    let db_path = metrics_store::default_db_path();
    let exporter = match SqliteMetricsExporter::open(&db_path) {
        Ok(e) => e,
        Err(e) => {
            eprintln!("cmdcrush: failed to open stats db at {}: {e}", db_path.display());
            return None;
        }
    };
    let reader = PeriodicReader::builder(exporter)
        .with_interval(Duration::from_secs(3600))
        .build();
    let provider = SdkMeterProvider::builder().with_reader(reader).build();
    let meter = provider.meter("cmdcrush");
    Some(Metrics {
        invocations: meter.u64_counter("cmdcrush.invocations").build(),
        bytes_before: meter.u64_histogram("cmdcrush.bytes_before").build(),
        bytes_after: meter.u64_histogram("cmdcrush.bytes_after").build(),
        provider,
    })
}

fn print_result(
    stats: bool,
    metrics: &Option<Metrics>,
    program: &str,
    label: &str,
    before: usize,
    after: usize,
    method: &str,
) {
    if let Some(m) = metrics {
        let attrs = [
            KeyValue::new("command", program.to_string()),
            KeyValue::new("label", label.to_string()),
            KeyValue::new("method", method.to_string()),
        ];
        m.invocations.add(1, &attrs);
        m.bytes_before.record(before as u64, &attrs);
        m.bytes_after.record(after as u64, &attrs);
    }

    if !stats {
        return;
    }
    let pct = if before == 0 {
        0.0
    } else {
        100.0 * (1.0 - after as f64 / before as f64)
    };
    eprintln!("cmdcrush: {label}: {before} -> {after} bytes via {method} ({pct:.1}% saved)");
}

/// Force a final export and shut down the meter provider so metrics survive
/// this short-lived process exiting, then exit with `code`.
fn finish(metrics: Option<Metrics>, code: i32) -> ! {
    if let Some(m) = metrics {
        // `shutdown()` already flushes pending telemetry — calling
        // `force_flush()` first would export the same data twice.
        if let Err(e) = m.provider.shutdown() {
            eprintln!("cmdcrush: failed to flush stats: {e}");
        }
    }
    std::process::exit(code);
}

fn main() {
    let cli = Cli::parse();

    if cli.history_stats {
        let dir = cli.history_dir.clone().unwrap_or_else(|| {
            let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
            PathBuf::from(home).join(".claude/projects")
        });
        run_history_stats(&dir, cli.floor_bytes, cli.max_lines, cli.top);
        return;
    }

    let Some((program, args)) = cli.command.split_first() else {
        eprintln!("cmdcrush: no command given (or pass --history-stats)");
        std::process::exit(2);
    };
    let cmd_label = command_label(program, args);
    let metrics = init_metrics();

    let mut child = Proc::new(program)
        .args(args)
        .stdin(Stdio::inherit())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap_or_else(|e| {
            eprintln!("cmdcrush: failed to execute `{program}`: {e}");
            std::process::exit(127);
        });

    let stdout_pipe = child.stdout.take().expect("piped stdout");
    let stderr_pipe = child.stderr.take().expect("piped stderr");

    let (tx, rx) = mpsc::channel();
    let tx2 = tx.clone();
    let out_handle = spawn_reader(stdout_pipe, Chunk::Stdout, tx);
    let err_handle = spawn_reader(stderr_pipe, Chunk::Stderr, tx2);

    let chunks: Vec<Chunk> = rx.into_iter().collect();
    out_handle.join().ok();
    err_handle.join().ok();

    let status = child.wait().unwrap_or_else(|e| {
        eprintln!("cmdcrush: failed to wait on `{program}`: {e}");
        std::process::exit(1);
    });

    let mut stdout_bytes = Vec::new();
    let mut stderr_bytes = Vec::new();
    for chunk in &chunks {
        match chunk {
            Chunk::Stdout(b) => stdout_bytes.extend_from_slice(b),
            Chunk::Stderr(b) => stderr_bytes.extend_from_slice(b),
        }
    }
    let has_stdout = !stdout_bytes.is_empty();
    let has_stderr = !stderr_bytes.is_empty();
    let mixed = has_stdout && has_stderr;

    let archive_dir = cli
        .archive_dir
        .clone()
        .unwrap_or_else(|| std::env::temp_dir().join("cmdcrush"));

    // Binary output can't be safely re-encoded or tagged with `[stderr] `
    // markers without corrupting it — pass it through untouched rather than
    // mangling it with `from_utf8_lossy`.
    let stdout_text = String::from_utf8(stdout_bytes.clone()).ok();
    let stderr_text = String::from_utf8(stderr_bytes.clone()).ok();

    if stdout_text.is_none() || stderr_text.is_none() {
        if stdout_text.is_none() && has_stdout {
            eprintln!("cmdcrush: stdout is not valid UTF-8 — passing through uncompressed");
        }
        if stderr_text.is_none() && has_stderr {
            eprintln!("cmdcrush: stderr is not valid UTF-8 — passing through uncompressed");
        }
        std::io::stdout().write_all(&stdout_bytes).ok();
        std::io::stderr().write_all(&stderr_bytes).ok();
        finish(metrics, status.code().unwrap_or(1));
    }
    let stdout_text = stdout_text.unwrap();
    let stderr_text = stderr_text.unwrap();

    let total_before = stdout_bytes.len() + stderr_bytes.len();
    if total_before < cli.floor_bytes {
        print_result(cli.stats, &metrics, &cmd_label, "combined", total_before, total_before, "below-floor");
        print!("{stdout_text}");
        eprint!("{stderr_text}");
        std::io::stdout().flush().ok();
        std::io::stderr().flush().ok();
        finish(metrics, status.code().unwrap_or(1));
    }

    let original_for_archive;
    let final_output;

    if mixed {
        // Rebuild in arrival order so the temporal relationship between the
        // two streams isn't silently discarded, tagging stderr lines since
        // they now share stdout with stdout lines.
        let mut merged = String::new();
        for chunk in &chunks {
            match chunk {
                Chunk::Stdout(b) => merged.push_str(&String::from_utf8_lossy(b)),
                Chunk::Stderr(b) => {
                    let line = String::from_utf8_lossy(b);
                    for l in line.split_inclusive('\n') {
                        if !l.is_empty() {
                            merged.push_str("[stderr] ");
                            merged.push_str(l);
                        }
                    }
                }
            }
        }
        let (compressed, method) = compress_text(&merged, cli.max_lines);
        print_result(cli.stats, &metrics, &cmd_label, "merged", merged.len(), compressed.len(), &method);
        original_for_archive = merged.into_bytes();
        final_output = compressed;

        if !cli.no_archive && final_output.len() < original_for_archive.len() {
            match archive_original(&original_for_archive, &archive_dir) {
                Ok(path) => eprintln!("cmdcrush: original archived at {}", path.display()),
                Err(e) => eprintln!("cmdcrush: failed to archive original: {e}"),
            }
        }

        print!("{final_output}");
        std::io::stdout().flush().ok();
    } else {
        // Only one stream had output — compress and print it to its own fd,
        // same contract as before.
        let (compressed_stdout, out_method) = if has_stdout {
            compress_text(&stdout_text, cli.max_lines)
        } else {
            (String::new(), "n/a".to_string())
        };
        let (compressed_stderr, err_method) = if has_stderr {
            compress_text(&stderr_text, cli.max_lines)
        } else {
            (String::new(), "n/a".to_string())
        };

        print_result(cli.stats, &metrics, &cmd_label, "stdout", stdout_text.len(), compressed_stdout.len(), &out_method);
        print_result(cli.stats, &metrics, &cmd_label, "stderr", stderr_text.len(), compressed_stderr.len(), &err_method);

        if !cli.no_archive {
            if compressed_stdout.len() < stdout_text.len() {
                if let Ok(path) = archive_original(stdout_text.as_bytes(), &archive_dir) {
                    eprintln!("cmdcrush: original stdout archived at {}", path.display());
                }
            }
            if compressed_stderr.len() < stderr_text.len() {
                if let Ok(path) = archive_original(stderr_text.as_bytes(), &archive_dir) {
                    eprintln!("cmdcrush: original stderr archived at {}", path.display());
                }
            }
        }

        print!("{compressed_stdout}");
        eprint!("{compressed_stderr}");
        std::io::stdout().flush().ok();
        std::io::stderr().flush().ok();
    }

    finish(metrics, status.code().unwrap_or(1));
}
