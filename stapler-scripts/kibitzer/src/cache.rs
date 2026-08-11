use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

use anyhow::Result;
use serde::{Deserialize, Serialize};

use crate::check::CheckResult;
use crate::config::Severity;

/// A cheap fingerprint of a file's on-disk state, used to invalidate cache entries
/// without hashing file contents.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
struct Stamp {
    mtime_secs: u64,
    mtime_nanos: u32,
    len: u64,
}

fn stamp(path: &Path) -> Option<Stamp> {
    let meta = fs::metadata(path).ok()?;
    let modified = meta.modified().ok()?;
    let dur = modified.duration_since(SystemTime::UNIX_EPOCH).ok()?;
    Some(Stamp {
        mtime_secs: dur.as_secs(),
        mtime_nanos: dur.subsec_nanos(),
        len: meta.len(),
    })
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CacheEntry {
    file_stamp: Stamp,
    /// Fingerprint of the config file whose checks produced `results` — a check
    /// definition edit (command/scope/severity) must invalidate cached results even
    /// if the target file itself didn't change.
    config_stamp: Stamp,
    trigger: String,
    results: Vec<CheckResult>,
}

/// Persistent, file-fingerprint-keyed cache of check results, shared across daemon
/// connections (and, via load/save, across daemon restarts) so unchanged files under
/// repeated `run`/`hook` invocations skip re-executing check commands entirely.
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct Cache {
    entries: HashMap<String, CacheEntry>,
    /// (file_path, check_name) pairs that have failed a blocking check at least once
    /// under a live per-edit trigger without yet passing again — see `apply_grace`.
    #[serde(default)]
    grace_pending: HashMap<String, bool>,
}

impl Cache {
    pub fn load(path: &Path) -> Self {
        fs::read_to_string(path)
            .ok()
            .and_then(|raw| serde_json::from_str(&raw).ok())
            .unwrap_or_default()
    }

    pub fn save(&self, path: &Path) -> Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, serde_json::to_string(self)?)?;
        Ok(())
    }

    pub fn get(
        &self,
        file_path: &Path,
        config_path: &Path,
        trigger: &str,
    ) -> Option<Vec<CheckResult>> {
        let file_stamp = stamp(file_path)?;
        let config_stamp = stamp(config_path)?;
        let entry = self.entries.get(&key(file_path))?;
        if entry.trigger == trigger
            && entry.file_stamp == file_stamp
            && entry.config_stamp == config_stamp
        {
            Some(entry.results.clone())
        } else {
            None
        }
    }

    pub fn put(
        &mut self,
        file_path: &Path,
        config_path: &Path,
        trigger: &str,
        results: Vec<CheckResult>,
    ) {
        let (Some(file_stamp), Some(config_stamp)) = (stamp(file_path), stamp(config_path))
        else {
            return;
        };
        self.entries.insert(
            key(file_path),
            CacheEntry {
                file_stamp,
                config_stamp,
                trigger: trigger.to_string(),
                results,
            },
        );
    }

    /// Give a first-time blocking failure one edit's grace before it actually blocks:
    /// the first time a given (file, check) pair fails under a live per-edit trigger
    /// (anything other than "batch"), downgrade it to advisory instead of blocking.
    /// Only escalate back to blocking if it's *still* failing the next time this file
    /// is checked — i.e. a multi-step edit (add a reference-style link use, then its
    /// definition in a later edit) gets one edit's worth of slack to self-correct, but
    /// a violation that never gets fixed still blocks on the very next touch. Batch
    /// mode (pre-commit-style, not a live hook) always enforces immediately.
    pub fn apply_grace(&mut self, results: &mut [CheckResult], file_path: &Path, trigger: &str) {
        if trigger == "batch" {
            return;
        }
        for result in results.iter_mut() {
            if result.severity != Severity::Blocking {
                continue;
            }
            let grace_key = format!("{}::{}", key(file_path), result.check_name);
            if result.passed {
                self.grace_pending.remove(&grace_key);
                continue;
            }
            if self.grace_pending.insert(grace_key, true) != Some(true) {
                result.severity = Severity::Advisory;
                result.output.push_str(
                    "\n[kibitzer] first occurrence this edit sequence — will block if still \
                     failing on the next edit to this file",
                );
            }
        }
    }
}

fn key(file_path: &Path) -> String {
    file_path.to_string_lossy().into_owned()
}

pub fn default_cache_path() -> PathBuf {
    if let Ok(dir) = std::env::var("XDG_CACHE_HOME") {
        return PathBuf::from(dir).join("kibitzer").join("cache.json");
    }
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".cache").join("kibitzer").join("cache.json")
}
