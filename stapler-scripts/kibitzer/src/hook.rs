use std::io::Read;
use std::path::PathBuf;
use std::process::ExitCode;

use anyhow::{Context, Result};
use serde::Deserialize;
use serde_json::json;

use crate::config::Severity;
use crate::daemon::run_checks_smart;

#[derive(Debug, Deserialize)]
struct HookInput {
    cwd: PathBuf,
    #[serde(default)]
    hook_event_name: String,
    #[serde(default)]
    tool_input: ToolInput,
}

#[derive(Debug, Default, Deserialize)]
struct ToolInput {
    file_path: Option<PathBuf>,
}

/// Implements the Claude Code `PostToolUse` hook contract: read the event off stdin,
/// run any in-scope checks, and report back via stdout (advisory) or exit 2 + stderr
/// (blocking).
pub fn run_hook() -> Result<ExitCode> {
    let mut raw = String::new();
    std::io::stdin()
        .read_to_string(&mut raw)
        .context("reading hook input from stdin")?;
    let input: HookInput = serde_json::from_str(&raw).context("parsing hook input JSON")?;

    let Some(file_path) = input.tool_input.file_path else {
        return Ok(ExitCode::SUCCESS);
    };

    let results = run_checks_smart(&input.cwd, &file_path, &input.hook_event_name)?;
    if results.is_empty() {
        return Ok(ExitCode::SUCCESS);
    }

    let failures: Vec<_> = results.iter().filter(|r| !r.passed).collect();
    if failures.is_empty() {
        return Ok(ExitCode::SUCCESS);
    }

    let blocking: Vec<_> = failures
        .iter()
        .filter(|r| r.severity == Severity::Blocking)
        .collect();

    if !blocking.is_empty() {
        for result in &blocking {
            eprintln!(
                "[kibitzer] {} (blocking): {}",
                result.check_name,
                result.message.as_deref().unwrap_or(&result.output)
            );
        }
        return Ok(ExitCode::from(2));
    }

    let context = failures
        .iter()
        .map(|r| {
            format!(
                "{}: {}",
                r.check_name,
                r.message.as_deref().unwrap_or(&r.output)
            )
        })
        .collect::<Vec<_>>()
        .join("\n");

    let payload = json!({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context,
        }
    });
    println!("{payload}");
    Ok(ExitCode::SUCCESS)
}
