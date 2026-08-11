mod cache;
mod check;
mod config;
mod daemon;
mod glob;
mod hook;
mod mcp;
mod primitive_obsession;
mod run;

use std::path::PathBuf;
use std::process::ExitCode;

use anyhow::Result;
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "kibitzer", about = "Cross-language code/doc inspection")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Batch mode: run checks for `trigger` against every file under `dir`.
    Run {
        #[arg(default_value = ".")]
        dir: PathBuf,
        #[arg(long, default_value = "batch")]
        trigger: String,
    },
    /// Claude Code PostToolUse hook mode: read the event off stdin.
    Hook,
    /// Run kibitzer as an MCP server over stdio.
    Mcp,
    /// Manage the background daemon that caches check results across invocations.
    Daemon {
        #[command(subcommand)]
        action: DaemonAction,
    },
    /// Run a specific built-in analysis directly against a file (for wiring into
    /// .claude/inspect.json's shell-command checks).
    Check {
        #[command(subcommand)]
        check: CheckCommand,
    },
}

#[derive(Subcommand)]
enum CheckCommand {
    /// Flag Go parameters that pile up the same primitive type (see
    /// .claude/rules/primitive-obsession-checklist.md).
    PrimitiveObsession { file: PathBuf },
}

#[derive(Subcommand)]
enum DaemonAction {
    /// Run the daemon in the foreground (background it yourself: `&`, systemd, launchd).
    Start,
    /// Ask a running daemon to shut down.
    Stop,
    /// Report whether a daemon is currently reachable.
    Status,
}

fn main() -> Result<ExitCode> {
    let cli = Cli::parse();
    match cli.command {
        Command::Run { dir, trigger } => run::run_batch(dir, &trigger),
        Command::Hook => hook::run_hook(),
        Command::Mcp => {
            let rt = tokio::runtime::Runtime::new()?;
            rt.block_on(mcp::run_mcp_server())?;
            Ok(ExitCode::SUCCESS)
        }
        Command::Daemon { action } => match action {
            DaemonAction::Start => {
                daemon::run_daemon(&daemon::default_socket_path())?;
                Ok(ExitCode::SUCCESS)
            }
            DaemonAction::Stop => {
                if daemon::shutdown() {
                    println!("[kibitzer] daemon stopped");
                } else {
                    println!("[kibitzer] no daemon was running");
                }
                Ok(ExitCode::SUCCESS)
            }
            DaemonAction::Status => {
                if daemon::is_alive() {
                    println!("[kibitzer] daemon is running");
                } else {
                    println!("[kibitzer] no daemon running");
                }
                Ok(ExitCode::SUCCESS)
            }
        },
        Command::Check { check } => match check {
            CheckCommand::PrimitiveObsession { file } => {
                let findings = primitive_obsession::check_file(&file)?;
                if findings.is_empty() {
                    Ok(ExitCode::SUCCESS)
                } else {
                    for finding in &findings {
                        println!("{}:{}: {}", file.display(), finding.line, finding.message);
                    }
                    Ok(ExitCode::from(1))
                }
            }
        },
    }
}
