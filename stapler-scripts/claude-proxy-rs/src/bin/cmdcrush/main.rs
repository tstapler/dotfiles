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
use sha2::{Digest, Sha256};

use claude_proxy_rs::compression::TextCompressor;

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

    /// Command (and its arguments) to run.
    #[arg(trailing_var_arg = true, required = true, num_args = 1..)]
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

/// Try to compress `text`: JSON is minified (key order may change — `Value`
/// uses a `BTreeMap` without the `preserve_order` feature — but structure
/// and content survive intact, unlike running line-oriented log heuristics
/// over it, which can delete lines that happen to repeat in valid JSON and
/// corrupt the syntax). Anything else goes through `TextCompressor`.
fn compress_text(text: &str) -> (String, &'static str) {
    if let Ok(value) = serde_json::from_str::<serde_json::Value>(text.trim()) {
        if let Ok(minified) = serde_json::to_string(&value) {
            if minified.len() < text.len() {
                return (minified, "json-minify");
            }
        }
        return (text.to_string(), "json-noop");
    }
    (TextCompressor::new().compress(text), "text")
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
    let (program, args) = cli
        .command
        .split_first()
        .expect("clap requires at least one command argument");
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
        print_result(cli.stats, &metrics, program, "combined", total_before, total_before, "below-floor");
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
        let (compressed, method) = compress_text(&merged);
        print_result(cli.stats, &metrics, program, "merged", merged.len(), compressed.len(), method);
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
            compress_text(&stdout_text)
        } else {
            (String::new(), "n/a")
        };
        let (compressed_stderr, err_method) = if has_stderr {
            compress_text(&stderr_text)
        } else {
            (String::new(), "n/a")
        };

        print_result(cli.stats, &metrics, program, "stdout", stdout_text.len(), compressed_stdout.len(), out_method);
        print_result(cli.stats, &metrics, program, "stderr", stderr_text.len(), compressed_stderr.len(), err_method);

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
