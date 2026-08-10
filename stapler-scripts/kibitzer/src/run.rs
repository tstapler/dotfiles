use std::path::PathBuf;
use std::process::ExitCode;

use anyhow::Result;

use crate::check::{run_check, run_checks_for_trigger, walk_and_collect_files, CheckResult};
use crate::config::{find_config, Check, Severity};

fn report(file_display: &str, result: &CheckResult) {
    if result.passed {
        return;
    }
    println!(
        "[{}] {} — {}: {}",
        match result.severity {
            Severity::Blocking => "BLOCKING",
            Severity::Advisory => "advisory",
        },
        file_display,
        result.check_name,
        result.message.as_deref().unwrap_or(&result.output)
    );
}

/// Batch mode: run every check whose `triggers` includes `trigger` (or has no
/// triggers at all) against every file under `dir`, reporting all failures.
///
/// Checks are split by whether `command` references `{file}`: a check without it is
/// whole-repo-scoped (e.g. `lychee --config lychee.toml .`, `python3 scripts/doc_report.py`)
/// and must run exactly once per batch invocation, not once per matched file — otherwise an
/// N-file repo re-runs an already-whole-repo command N times (confirmed: ~22x, >90s, against
/// design-docs' ~22 markdown files).
pub fn run_batch(dir: PathBuf, trigger: &str) -> Result<ExitCode> {
    let Some((config, repo_root)) = find_config(&dir)? else {
        eprintln!("[kibitzer] no .claude/inspect.json found above {}", dir.display());
        return Ok(ExitCode::SUCCESS);
    };

    let (repo_checks, file_checks): (Vec<Check>, Vec<Check>) = config
        .checks
        .into_iter()
        .partition(|c| !c.command.contains("{file}"));

    let mut any_blocking_failure = false;

    for check in &repo_checks {
        if !check.triggers.is_empty() && !check.triggers.iter().any(|t| t == trigger) {
            continue;
        }
        let result = run_check(check, &repo_root, &repo_root)?;
        if !result.passed && result.severity == Severity::Blocking {
            any_blocking_failure = true;
        }
        report(&repo_root.display().to_string(), &result);
    }

    let files = walk_and_collect_files(&dir)?;
    for file in files {
        for result in run_checks_for_trigger(&file_checks, trigger, &repo_root, &file)? {
            if !result.passed && result.severity == Severity::Blocking {
                any_blocking_failure = true;
            }
            report(&file.display().to_string(), &result);
        }
    }

    if any_blocking_failure {
        Ok(ExitCode::from(1))
    } else {
        Ok(ExitCode::SUCCESS)
    }
}
