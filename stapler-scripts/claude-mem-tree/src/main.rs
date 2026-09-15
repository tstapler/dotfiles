//! claude-mem-tree: live memory tree for a Claude Code process and its
//! descendants (MCP servers, spawned test runners, subshells).
//!
//! Reads /proc directly — no Python/procpath dependency. Linux only.
//!
//! RSS comes from /proc/[pid]/status (VmRSS). PSS (proportional set size —
//! shared pages counted once, divided across the processes sharing them)
//! comes from /proc/[pid]/smaps_rollup and is the number that actually sums
//! to "how much RAM does this tree use", since Node/Bun/MCP children share
//! a lot of mapped library pages that RSS would double-count.

use std::collections::HashMap;
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::PathBuf;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use anyhow::{bail, Context, Result};
use clap::Parser;
use crossterm::{
    event::{self, Event, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
    text::Span,
    widgets::{Block, Borders, Cell, Paragraph, Row, Table},
    Frame, Terminal,
};

#[derive(Parser)]
#[command(
    author,
    version,
    about = "Live memory tree for a Claude Code process and its children (MCP servers, spawned test runners, ...)"
)]
struct Args {
    /// PID to root the tree at. Default: nearest ancestor process named `claude`.
    #[arg(long)]
    pid: Option<i32>,

    /// Refresh interval in milliseconds.
    #[arg(long, default_value_t = 1000)]
    interval_ms: u64,

    /// Print one snapshot as plain text and exit, instead of the live TUI.
    #[arg(long)]
    once: bool,

    /// Append a CSV row per process per refresh (ts,pid,depth,comm,rss_kb,pss_kb).
    #[arg(long)]
    log: Option<PathBuf>,

    /// Highlight a row once its PSS reaches this many MB.
    #[arg(long, default_value_t = 200)]
    warn_mb: u64,
}

#[derive(Clone)]
struct ProcInfo {
    ppid: i32,
    comm: String,
    rss_kb: u64,
}

struct TreeRow {
    pid: i32,
    depth: usize,
    comm: String,
    rss_kb: u64,
    pss_kb: Option<u64>,
}

// ── /proc reading ───────────────────────────────────────────────────────────

fn read_status(pid: i32) -> Option<ProcInfo> {
    let text = fs::read_to_string(format!("/proc/{pid}/status")).ok()?;
    let mut comm = String::new();
    let mut ppid = -1;
    let mut rss_kb = 0;
    for line in text.lines() {
        if let Some(v) = line.strip_prefix("Name:") {
            comm = v.trim().to_string();
        } else if let Some(v) = line.strip_prefix("PPid:") {
            ppid = v.trim().parse().unwrap_or(-1);
        } else if let Some(v) = line.strip_prefix("VmRSS:") {
            rss_kb = v.trim().trim_end_matches("kB").trim().parse().unwrap_or(0);
        }
    }
    Some(ProcInfo { ppid, comm, rss_kb })
}

fn read_pss_kb(pid: i32) -> Option<u64> {
    let text = fs::read_to_string(format!("/proc/{pid}/smaps_rollup")).ok()?;
    text.lines()
        .find_map(|l| l.strip_prefix("Pss:"))
        .and_then(|v| v.trim().trim_end_matches("kB").trim().parse().ok())
}

fn read_all_procs() -> HashMap<i32, ProcInfo> {
    let mut out = HashMap::new();
    let Ok(entries) = fs::read_dir("/proc") else { return out };
    for entry in entries.flatten() {
        if let Some(pid) = entry.file_name().to_str().and_then(|s| s.parse::<i32>().ok()) {
            if let Some(info) = read_status(pid) {
                out.insert(pid, info);
            }
        }
    }
    out
}

fn find_claude_ancestor() -> Result<i32> {
    let mut pid = read_status(std::process::id() as i32)
        .context("reading /proc/self/status")?
        .ppid;
    loop {
        if pid <= 1 {
            bail!("no ancestor process named `claude` found — pass --pid explicitly");
        }
        let info = read_status(pid)
            .with_context(|| format!("ancestor PID {pid} vanished while walking up — pass --pid explicitly"))?;
        if info.comm == "claude" {
            return Ok(pid);
        }
        pid = info.ppid;
    }
}

// ── tree building ────────────────────────────────────────────────────────────

fn build_children_map(all: &HashMap<i32, ProcInfo>) -> HashMap<i32, Vec<i32>> {
    let mut children: HashMap<i32, Vec<i32>> = HashMap::new();
    for (&pid, info) in all {
        children.entry(info.ppid).or_default().push(pid);
    }
    children
}

/// Every PID reachable here is our own descendant, so smaps_rollup is always
/// readable — unlike scanning the whole system, there's no permission noise.
fn collect_pss(all: &HashMap<i32, ProcInfo>, children: &HashMap<i32, Vec<i32>>, root: i32) -> HashMap<i32, Option<u64>> {
    let mut pss = HashMap::new();
    let mut stack = vec![root];
    while let Some(pid) = stack.pop() {
        if !all.contains_key(&pid) {
            continue;
        }
        pss.insert(pid, read_pss_kb(pid));
        if let Some(kids) = children.get(&pid) {
            stack.extend(kids);
        }
    }
    pss
}

/// Pre-order DFS from `root`. Within each parent, children are ordered by
/// PSS (falling back to RSS when PSS isn't readable) descending, so the
/// biggest consumer in any branch is always listed first — while
/// indentation still reflects the real parent/child structure.
fn build_tree(all: &HashMap<i32, ProcInfo>, root: i32) -> Vec<TreeRow> {
    let children = build_children_map(all);
    let pss = collect_pss(all, &children, root);
    let weight = |pid: i32| -> u64 {
        pss.get(&pid)
            .copied()
            .flatten()
            .unwrap_or_else(|| all.get(&pid).map(|i| i.rss_kb).unwrap_or(0))
    };

    let mut rows = Vec::new();
    let mut stack = vec![(root, 0usize)];
    while let Some((pid, depth)) = stack.pop() {
        let Some(info) = all.get(&pid) else { continue };
        rows.push(TreeRow {
            pid,
            depth,
            comm: info.comm.clone(),
            rss_kb: info.rss_kb,
            pss_kb: pss.get(&pid).copied().flatten(),
        });
        if let Some(kids) = children.get(&pid) {
            let mut kids = kids.clone();
            kids.sort_by_key(|&p| std::cmp::Reverse(weight(p)));
            stack.extend(kids.into_iter().rev().map(|k| (k, depth + 1)));
        }
    }
    rows
}

// ── output: plain text + CSV log ────────────────────────────────────────────

fn append_log(path: &PathBuf, rows: &[TreeRow]) -> Result<()> {
    let is_new = !path.exists();
    let mut f = OpenOptions::new().create(true).append(true).open(path)?;
    if is_new {
        writeln!(f, "ts,pid,depth,comm,rss_kb,pss_kb")?;
    }
    let ts = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    for r in rows {
        writeln!(
            f,
            "{ts},{},{},{},{},{}",
            r.pid,
            r.depth,
            r.comm,
            r.rss_kb,
            r.pss_kb.map(|v| v.to_string()).unwrap_or_default()
        )?;
    }
    Ok(())
}

fn print_once(rows: &[TreeRow], warn_mb: u64) {
    let total_pss_kb: u64 = rows.iter().filter_map(|r| r.pss_kb).sum();
    println!("PID       RSS(MB)  PSS(MB)  TREE");
    for r in rows {
        let indent = "  ".repeat(r.depth);
        let pss_mb = r.pss_kb.map(|v| v / 1024);
        let marker = if pss_mb.is_some_and(|mb| mb >= warn_mb) { " ⚠" } else { "" };
        println!(
            "{:<9} {:>7} {:>8}  {indent}{}{marker}",
            r.pid,
            r.rss_kb / 1024,
            pss_mb.map(|v| v.to_string()).unwrap_or_else(|| "-".into()),
            r.comm,
        );
    }
    println!("\nTotal PSS: {} MB across {} processes", total_pss_kb / 1024, rows.len());
}

// ── TUI ──────────────────────────────────────────────────────────────────────

fn row_style(r: &TreeRow, warn_mb: u64) -> Style {
    let hot = r.pss_kb.is_some_and(|v| v / 1024 >= warn_mb);
    if hot {
        Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)
    } else if r.depth == 0 {
        Style::default().fg(Color::Yellow)
    } else {
        Style::default()
    }
}

fn tree_row_widget(r: &TreeRow, warn_mb: u64) -> Row<'static> {
    let pss_mb = r.pss_kb.map(|v| v / 1024);
    let indent = "  ".repeat(r.depth);
    let branch = if r.depth == 0 { "" } else { "└─ " };
    Row::new(vec![
        Cell::from(r.pid.to_string()),
        Cell::from((r.rss_kb / 1024).to_string()),
        Cell::from(pss_mb.map(|v| v.to_string()).unwrap_or_else(|| "-".into())),
        Cell::from(format!("{indent}{branch}{}", r.comm)),
    ])
    .style(row_style(r, warn_mb))
}

fn render(f: &mut Frame, rows: &[TreeRow], root: i32, warn_mb: u64) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(5), Constraint::Length(2)])
        .split(f.area());

    let total_pss_kb: u64 = rows.iter().filter_map(|r| r.pss_kb).sum();
    let title = format!(" claude-mem-tree  root={root}  total PSS: {} MB ", total_pss_kb / 1024);

    let header = Row::new(vec![
        Cell::from("PID"),
        Cell::from("RSS(MB)"),
        Cell::from("PSS(MB)"),
        Cell::from("PROCESS TREE"),
    ])
    .style(Style::default().add_modifier(Modifier::BOLD).fg(Color::Cyan))
    .height(1);

    let table_rows: Vec<Row> = rows.iter().map(|r| tree_row_widget(r, warn_mb)).collect();
    let widths = [
        Constraint::Length(9),
        Constraint::Length(9),
        Constraint::Length(9),
        Constraint::Min(30),
    ];
    let table = Table::new(table_rows, widths)
        .header(header)
        .block(Block::default().borders(Borders::ALL).title(Span::raw(title)));

    f.render_widget(table, chunks[0]);
    f.render_widget(
        Paragraph::new(" [q] quit   red = PSS at or above --warn-mb ").style(Style::default().fg(Color::DarkGray)),
        chunks[1],
    );
}

fn should_quit(event: Event) -> bool {
    matches!(
        event,
        Event::Key(key)
            if matches!(
                (key.modifiers, key.code),
                (_, KeyCode::Char('q')) | (KeyModifiers::CONTROL, KeyCode::Char('c'))
            )
    )
}

/// Re-reads /proc and rebuilds the tree; `Ok(None)` means the root process
/// has exited and the caller should stop.
fn refresh(root: i32, log: &Option<PathBuf>) -> Result<Option<Vec<TreeRow>>> {
    let all = read_all_procs();
    if !all.contains_key(&root) {
        return Ok(None);
    }
    let rows = build_tree(&all, root);
    if let Some(p) = log {
        append_log(p, &rows)?;
    }
    Ok(Some(rows))
}

fn event_loop(
    terminal: &mut Terminal<CrosstermBackend<io::Stdout>>,
    root: i32,
    interval: Duration,
    log: &Option<PathBuf>,
    warn_mb: u64,
) -> Result<()> {
    let mut rows = build_tree(&read_all_procs(), root);
    loop {
        terminal.draw(|f| render(f, &rows, root, warn_mb))?;

        if !event::poll(interval)? {
            match refresh(root, log)? {
                Some(next) => rows = next,
                None => return Ok(()),
            }
            continue;
        }
        if should_quit(event::read()?) {
            return Ok(());
        }
    }
}

fn run_tui(root: i32, interval: Duration, log: Option<PathBuf>, warn_mb: u64) -> Result<()> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let mut terminal = Terminal::new(CrosstermBackend::new(stdout))?;

    let result = event_loop(&mut terminal, root, interval, &log, warn_mb);

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    result
}

fn main() -> Result<()> {
    let args = Args::parse();
    let root = match args.pid {
        Some(p) => p,
        None => find_claude_ancestor()?,
    };
    if read_status(root).is_none() {
        bail!("PID {root} not found");
    }

    if args.once {
        let rows = build_tree(&read_all_procs(), root);
        if let Some(p) = &args.log {
            append_log(p, &rows)?;
        }
        print_once(&rows, args.warn_mb);
        return Ok(());
    }

    run_tui(root, Duration::from_millis(args.interval_ms), args.log, args.warn_mb)
}
