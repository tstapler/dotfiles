use std::path::{Path, PathBuf};
use std::process::Command;

use serde::{Deserialize, Serialize};

use crate::config::{Check, Severity};
use crate::glob::matches_scope;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckResult {
    pub check_name: String,
    pub severity: Severity,
    pub passed: bool,
    pub output: String,
    pub message: Option<String>,
}

/// Run a single check against `file_path` (already confirmed in-scope by the caller).
pub fn run_check(check: &Check, repo_root: &Path, file_path: &Path) -> anyhow::Result<CheckResult> {
    let cmd_str = check.command.replace("{file}", &file_path.display().to_string());
    let output = Command::new("sh")
        .arg("-c")
        .arg(&cmd_str)
        .current_dir(repo_root)
        .output()?;

    let passed = output.status.success();
    let mut combined = String::from_utf8_lossy(&output.stdout).into_owned();
    combined.push_str(&String::from_utf8_lossy(&output.stderr));

    let mut severity = check.severity;
    let mut message = check.message.clone();

    if !passed && severity == Severity::Blocking && check.command.contains("{file}") {
        if let Some(false) = check_against_git_head(check, repo_root, file_path) {
            severity = Severity::Advisory;
            message = Some(format!(
                "{} (downgraded: this violation predates your edits — already present in \
                 the git HEAD version of this file)",
                message.unwrap_or_default()
            ));
        }
    }

    Ok(CheckResult {
        check_name: check.name.clone(),
        severity,
        passed,
        output: combined,
        message,
    })
}

/// Re-run `check` against the file's `git show HEAD:<relpath>` content to determine
/// whether a current failure predates this session's edits. Returns `Some(true)` if the
/// baseline also fails (pre-existing violation, not introduced by the current edit),
/// `Some(false)` if the baseline passes (the edit genuinely introduced this failure), or
/// `None` if the baseline can't be determined (untracked file, no HEAD, not a git repo,
/// etc.) — callers should treat `None` as "can't tell, don't suppress."
fn check_against_git_head(check: &Check, repo_root: &Path, file_path: &Path) -> Option<bool> {
    let rel_path = relativize(repo_root, file_path);
    let show = Command::new("git")
        .args(["show", &format!("HEAD:{rel_path}")])
        .current_dir(repo_root)
        .output()
        .ok()?;
    if !show.status.success() {
        return None;
    }

    let ext = file_path.extension().and_then(|e| e.to_str()).unwrap_or("");
    let mut tmp_path = file_path.to_path_buf();
    let tmp_name = format!(
        ".kibitzer-head-{}{}",
        std::process::id(),
        if ext.is_empty() { String::new() } else { format!(".{ext}") }
    );
    tmp_path.set_file_name(tmp_name);
    std::fs::write(&tmp_path, &show.stdout).ok()?;

    let cmd_str = check.command.replace("{file}", &tmp_path.display().to_string());
    let result = Command::new("sh")
        .arg("-c")
        .arg(&cmd_str)
        .current_dir(repo_root)
        .output();

    let _ = std::fs::remove_file(&tmp_path);

    result.ok().map(|out| out.status.success())
}

/// Run every check in `checks` that applies to `trigger` and whose scope matches
/// `file_path` (given relative to `repo_root`).
pub fn run_checks_for_trigger(
    checks: &[Check],
    trigger: &str,
    repo_root: &Path,
    file_path: &Path,
) -> anyhow::Result<Vec<CheckResult>> {
    let rel_path = relativize(repo_root, file_path);
    let mut results = Vec::new();
    for check in checks {
        if !check.triggers.is_empty() && !check.triggers.iter().any(|t| t == trigger) {
            continue;
        }
        if !matches_scope(&rel_path, &check.scope) {
            continue;
        }
        results.push(run_check(check, repo_root, file_path)?);
    }
    Ok(results)
}

fn relativize(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

/// Convenience for batch mode: walk `dir` and run checks against every file within it.
pub fn walk_and_collect_files(dir: &Path) -> anyhow::Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    for entry in walk(dir)? {
        if entry.is_file() {
            files.push(entry);
        }
    }
    Ok(files)
}

/// Directories never worth descending into for batch-mode scans: VCS internals and
/// dependency/build trees that can contain vendored source (e.g. flatted's bundled
/// Go port under node_modules) which isn't code this repo owns.
const SKIP_DIRS: &[&str] = &[
    ".git",
    "node_modules",
    "vendor",
    "target",
    "dist",
    "build",
    ".next",
];

fn walk(dir: &Path) -> anyhow::Result<Vec<PathBuf>> {
    let mut out = Vec::new();
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if path
            .file_name()
            .and_then(|n| n.to_str())
            .is_some_and(|name| SKIP_DIRS.contains(&name))
        {
            continue;
        }
        if path.is_dir() {
            out.extend(walk(&path)?);
        } else {
            out.push(path);
        }
    }
    Ok(out)
}
