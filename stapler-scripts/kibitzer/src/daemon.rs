use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

use crate::cache::{default_cache_path, Cache};
use crate::check::{run_checks_for_trigger, CheckResult};
use crate::config::{find_config, CONFIG_DIR, CONFIG_FILENAME};

#[derive(Debug, Serialize, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case")]
enum Request {
    RunChecks {
        cwd: PathBuf,
        file_path: PathBuf,
        trigger: String,
    },
    Ping,
    Shutdown,
}

#[derive(Debug, Serialize, Deserialize)]
struct Response {
    ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    results: Option<Vec<CheckResult>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}

/// Per-user socket path so multiple users on a shared machine never collide, and so a
/// leftover socket from a previous login session doesn't get reused across reboots
/// unexpectedly (XDG_RUNTIME_DIR is normally tmpfs, reset on boot).
pub fn default_socket_path() -> PathBuf {
    let base = std::env::var("XDG_RUNTIME_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| std::env::temp_dir());
    let user = std::env::var("USER").unwrap_or_else(|_| "kibitzer".to_string());
    base.join(format!("kibitzer-{user}.sock"))
}

/// Run the daemon in the foreground on `socket_path` until it receives a `Shutdown`
/// request or the process is killed. Callers that want it in the background are
/// expected to background it themselves (`kibitzer daemon &`, a systemd/launchd unit,
/// etc.) — the daemon does not self-detach.
pub fn run_daemon(socket_path: &Path) -> Result<()> {
    if socket_path.exists() {
        // A stale socket from a crashed prior daemon; a live daemon would have failed
        // to start in the first place (see `is_alive` check callers should do first).
        std::fs::remove_file(socket_path).ok();
    }
    let listener = UnixListener::bind(socket_path)
        .with_context(|| format!("binding daemon socket at {}", socket_path.display()))?;
    eprintln!("[kibitzer] daemon listening on {}", socket_path.display());

    let cache_path = default_cache_path();
    let cache = Arc::new(Mutex::new(Cache::load(&cache_path)));

    for stream in listener.incoming() {
        let stream = stream?;
        let cache = Arc::clone(&cache);
        let cache_path = cache_path.clone();
        std::thread::spawn(move || {
            if let Err(e) = handle_conn(stream, &cache, &cache_path) {
                eprintln!("[kibitzer] daemon connection error: {e}");
            }
        });
    }
    Ok(())
}

fn handle_conn(stream: UnixStream, cache: &Arc<Mutex<Cache>>, cache_path: &Path) -> Result<()> {
    let mut reader = BufReader::new(stream.try_clone()?);
    let mut writer = stream;
    let mut line = String::new();
    loop {
        line.clear();
        let n = reader.read_line(&mut line)?;
        if n == 0 {
            break;
        }
        let response = match serde_json::from_str::<Request>(&line) {
            Ok(Request::Ping) => Response {
                ok: true,
                results: None,
                error: None,
            },
            Ok(Request::Shutdown) => {
                let ack = Response {
                    ok: true,
                    results: None,
                    error: None,
                };
                writeln!(writer, "{}", serde_json::to_string(&ack)?)?;
                writer.flush()?;
                std::process::exit(0);
            }
            Ok(Request::RunChecks {
                cwd,
                file_path,
                trigger,
            }) => match handle_run_checks(&cwd, &file_path, &trigger, cache, cache_path) {
                Ok(results) => Response {
                    ok: true,
                    results: Some(results),
                    error: None,
                },
                Err(e) => Response {
                    ok: false,
                    results: None,
                    error: Some(e.to_string()),
                },
            },
            Err(e) => Response {
                ok: false,
                results: None,
                error: Some(format!("bad request: {e}")),
            },
        };
        writeln!(writer, "{}", serde_json::to_string(&response)?)?;
        writer.flush()?;
    }
    Ok(())
}

fn handle_run_checks(
    cwd: &Path,
    file_path: &Path,
    trigger: &str,
    cache: &Arc<Mutex<Cache>>,
    cache_path: &Path,
) -> Result<Vec<CheckResult>> {
    let Some((config, repo_root)) = find_config(cwd)? else {
        return Ok(Vec::new());
    };
    let config_path = repo_root.join(CONFIG_DIR).join(CONFIG_FILENAME);

    if let Ok(guard) = cache.lock()
        && let Some(cached) = guard.get(file_path, &config_path, trigger)
    {
        return Ok(cached);
    }

    let results = run_checks_for_trigger(&config.checks, trigger, &repo_root, file_path)?;

    if let Ok(mut guard) = cache.lock() {
        guard.put(file_path, &config_path, trigger, results.clone());
        let _ = guard.save(cache_path);
    }
    Ok(results)
}

fn connect() -> Option<UnixStream> {
    let stream = UnixStream::connect(default_socket_path()).ok()?;
    stream
        .set_read_timeout(Some(Duration::from_secs(30)))
        .ok()?;
    Some(stream)
}

/// True if a kibitzer daemon is listening and responds to a ping.
pub fn is_alive() -> bool {
    request(&Request::Ping).is_some()
}

pub fn shutdown() -> bool {
    request(&Request::Shutdown).is_some()
}

fn request(req: &Request) -> Option<Response> {
    let mut stream = connect()?;
    let mut payload = serde_json::to_string(req).ok()?;
    payload.push('\n');
    stream.write_all(payload.as_bytes()).ok()?;
    let mut reader = BufReader::new(stream);
    let mut line = String::new();
    reader.read_line(&mut line).ok()?;
    serde_json::from_str(&line).ok()
}

/// Ask the daemon to run checks for `file_path`/`trigger`, if one is reachable.
/// Returns `None` (rather than an error) when no daemon is running so callers can
/// transparently fall back to running the checks in-process.
pub fn try_run_checks_via_daemon(
    cwd: &Path,
    file_path: &Path,
    trigger: &str,
) -> Option<Vec<CheckResult>> {
    let response = request(&Request::RunChecks {
        cwd: cwd.to_path_buf(),
        file_path: file_path.to_path_buf(),
        trigger: trigger.to_string(),
    })?;
    if response.ok {
        response.results
    } else {
        None
    }
}

/// Run checks via the daemon if one is up, otherwise run them directly in-process
/// (uncached). This is the entry point `hook`/`run` should use instead of calling
/// `find_config` + `run_checks_for_trigger` themselves.
pub fn run_checks_smart(cwd: &Path, file_path: &Path, trigger: &str) -> Result<Vec<CheckResult>> {
    if let Some(results) = try_run_checks_via_daemon(cwd, file_path, trigger) {
        return Ok(results);
    }
    let Some((config, repo_root)) = find_config(cwd)? else {
        return Ok(Vec::new());
    };
    run_checks_for_trigger(&config.checks, trigger, &repo_root, file_path)
}
