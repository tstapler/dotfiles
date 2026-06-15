use std::collections::{HashMap, HashSet};
use std::fmt;
use std::fs;
use std::io::{self, Write};
use std::mem::discriminant;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use anyhow::{bail, Context, Result};
use clap::{Parser, Subcommand, ValueEnum};
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
    widgets::{Block, Borders, Cell, Paragraph, Row, Table, TableState},
    Frame, Terminal,
};

// ── VDF text parser ───────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
enum Vdf {
    Str(String),
    Map(HashMap<String, Vdf>),
}

impl Vdf {
    fn get(&self, key: &str) -> Option<&Vdf> {
        if let Vdf::Map(m) = self { m.get(key) } else { None }
    }
    fn as_str(&self) -> Option<&str> {
        if let Vdf::Str(s) = self { Some(s) } else { None }
    }
    fn as_u64(&self) -> Option<u64> {
        self.as_str()?.parse().ok()
    }
    fn as_map(&self) -> Option<&HashMap<String, Vdf>> {
        if let Vdf::Map(m) = self { Some(m) } else { None }
    }
    fn nav(&self, path: &[&str]) -> Option<&Vdf> {
        path.iter().try_fold(self, |v, k| v.get(k))
    }
}

struct VdfParser<'a> {
    src: &'a [u8],
    pos: usize,
}

impl<'a> VdfParser<'a> {
    fn new(s: &'a str) -> Self {
        Self { src: s.as_bytes(), pos: 0 }
    }

    fn skip_ws(&mut self) {
        loop {
            while self.pos < self.src.len() && self.src[self.pos].is_ascii_whitespace() {
                self.pos += 1;
            }
            if self.pos + 1 < self.src.len()
                && self.src[self.pos] == b'/'
                && self.src[self.pos + 1] == b'/'
            {
                while self.pos < self.src.len() && self.src[self.pos] != b'\n' {
                    self.pos += 1;
                }
            } else {
                break;
            }
        }
    }

    fn peek(&mut self) -> Option<u8> {
        self.skip_ws();
        self.src.get(self.pos).copied()
    }

    fn read_string(&mut self) -> Result<String> {
        self.skip_ws();
        if self.src.get(self.pos) != Some(&b'"') {
            bail!("expected '\"' at byte {}", self.pos);
        }
        self.pos += 1;
        let mut s = String::new();
        loop {
            match self.src.get(self.pos) {
                None => bail!("unterminated string"),
                Some(&b'\\') if self.pos + 1 < self.src.len() => {
                    self.pos += 1;
                    s.push(self.src[self.pos] as char);
                    self.pos += 1;
                }
                Some(&b'"') => { self.pos += 1; return Ok(s); }
                Some(&b) => { s.push(b as char); self.pos += 1; }
            }
        }
    }

    fn read_map(&mut self) -> Result<Vdf> {
        self.skip_ws();
        if self.src.get(self.pos) != Some(&b'{') {
            bail!("expected '{{' at byte {}", self.pos);
        }
        self.pos += 1;
        let mut map = HashMap::new();
        loop {
            match self.peek() {
                None => bail!("unexpected EOF inside map"),
                Some(b'}') => { self.pos += 1; break; }
                Some(b'"') => {
                    let key = self.read_string()?;
                    let val = match self.peek() {
                        Some(b'{') => self.read_map()?,
                        Some(b'"') => Vdf::Str(self.read_string()?),
                        other => bail!("unexpected {:?} after key {key:?}", other),
                    };
                    map.insert(key, val);
                }
                Some(b) => bail!("unexpected byte {b:#x} in map"),
            }
        }
        Ok(Vdf::Map(map))
    }

    fn parse_root(&mut self) -> Result<Vdf> {
        let mut map = HashMap::new();
        loop {
            match self.peek() {
                None | Some(b'}') => break,
                Some(b'"') => {
                    let key = self.read_string()?;
                    let val = match self.peek() {
                        Some(b'{') => self.read_map()?,
                        Some(b'"') => Vdf::Str(self.read_string()?),
                        other => bail!("unexpected {:?} after key {key:?}", other),
                    };
                    map.insert(key, val);
                }
                Some(b) => bail!("unexpected byte {b:#x} at root"),
            }
        }
        Ok(Vdf::Map(map))
    }
}

fn parse_vdf(s: &str) -> Result<Vdf> {
    VdfParser::new(s).parse_root()
}

// ── Game model ────────────────────────────────────────────────────────────────

const NEVER: u64 = 86_400; // Steam's sentinel for "never played"

#[derive(Debug, Clone)]
struct Game {
    appid: u64,
    name: String,
    size_bytes: u64,
    install_dir: String,
    library: PathBuf,
    last_played: u64,
    playtime_min: u64,
}

impl Game {
    fn size_gib(&self) -> f64 { self.size_bytes as f64 / 1_073_741_824.0 }
    fn playtime_hours(&self) -> f64 { self.playtime_min as f64 / 60.0 }

    fn days_idle(&self) -> u64 {
        if self.last_played <= NEVER { return 3_650; }
        let now = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
        now.saturating_sub(self.last_played) / 86_400
    }

    /// size_GiB × days_idle ÷ max(playtime_hours, 0.5)
    fn score(&self) -> f64 {
        self.size_gib() * self.days_idle() as f64 / self.playtime_hours().max(0.5)
    }

    fn last_played_str(&self) -> String {
        if self.last_played <= NEVER { return "never".into(); }
        match self.days_idle() {
            0 => "today".into(),
            1 => "yesterday".into(),
            d if d < 30 => format!("{d}d ago"),
            d if d < 365 => format!("{}mo ago", d / 30),
            d => format!("{}y ago", d / 365),
        }
    }

    fn playtime_str(&self) -> String {
        match self.playtime_min {
            0 => "-".into(),
            m if m < 60 => format!("{m}m"),
            m => format!("{}h", m / 60),
        }
    }
}

fn truncate(s: &str, max: usize) -> &str {
    let end = s.char_indices().nth(max).map(|(i, _)| i).unwrap_or(s.len());
    &s[..end]
}

// ── Filtering helpers ─────────────────────────────────────────────────────────

fn is_tool(g: &Game) -> bool {
    const SKIP: &[&str] = &[
        "runtime", "redistributable", "soundtrack", "ost",
        "dedicated server", "sdk", "steamworks", "proton",
    ];
    if g.size_bytes < 200_000_000 && g.last_played == 0 { return true; }
    let lower = g.name.to_lowercase();
    SKIP.iter().any(|w| lower.contains(w))
}

// ── Steam data loading ────────────────────────────────────────────────────────

struct PlayRecord { last_played: u64, playtime_min: u64 }

fn find_steam_root() -> Result<PathBuf> {
    let p = dirs::home_dir().context("no home dir")?.join(".local/share/Steam");
    if p.exists() { Ok(p) } else { bail!("Steam not found at {}", p.display()) }
}

fn find_library_roots(steam_root: &Path) -> Result<Vec<PathBuf>> {
    let path = steam_root.join("steamapps/libraryfolders.vdf");
    let vdf = parse_vdf(&fs::read_to_string(&path)?)?;
    let mut roots = vec![steam_root.to_path_buf()];
    if let Some(folders) = vdf.nav(&["libraryfolders"]).and_then(|v| v.as_map()) {
        for val in folders.values() {
            if let Some(p) = val.get("path").and_then(|v| v.as_str()) {
                let pb = PathBuf::from(p);
                if pb.exists() && !roots.contains(&pb) { roots.push(pb); }
            }
        }
    }
    Ok(roots)
}

fn load_play_records(steam_root: &Path) -> Result<HashMap<u64, PlayRecord>> {
    let best = fs::read_dir(steam_root.join("userdata"))?
        .flatten()
        .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
        .max_by_key(|e| {
            fs::metadata(e.path().join("config/localconfig.vdf"))
                .map(|m| m.len()).unwrap_or(0)
        });
    let Some(user) = best else { return Ok(HashMap::new()); };
    let content = fs::read_to_string(user.path().join("config/localconfig.vdf"))?;
    let vdf = parse_vdf(&content)?;
    let path = &["UserLocalConfigStore", "Software", "Valve", "Steam", "apps"];
    let Some(apps) = vdf.nav(path).and_then(|v| v.as_map()) else { return Ok(HashMap::new()); };
    Ok(apps.iter().filter_map(|(k, v)| {
        let appid = k.parse::<u64>().ok()?;
        Some((appid, PlayRecord {
            last_played: v.get("LastPlayed").and_then(|x| x.as_u64()).unwrap_or(0),
            playtime_min: v.get("Playtime").and_then(|x| x.as_u64()).unwrap_or(0),
        }))
    }).collect())
}

fn parse_acf(path: &Path, library: &Path, play: &HashMap<u64, PlayRecord>) -> Result<Game> {
    let vdf = parse_vdf(&fs::read_to_string(path)?)?;
    let s = vdf.get("AppState").context("missing AppState")?;
    let appid = s.get("appid").and_then(|v| v.as_u64()).context("missing appid")?;
    let (last_played, playtime_min) = match play.get(&appid) {
        Some(r) => (r.last_played.max(s.get("LastPlayed").and_then(|v| v.as_u64()).unwrap_or(0)), r.playtime_min),
        None => (s.get("LastPlayed").and_then(|v| v.as_u64()).unwrap_or(0), 0),
    };
    Ok(Game {
        appid,
        name: s.get("name").and_then(|v| v.as_str()).unwrap_or("?").into(),
        size_bytes: s.get("SizeOnDisk").and_then(|v| v.as_u64()).unwrap_or(0),
        install_dir: s.get("installdir").and_then(|v| v.as_str()).unwrap_or("").into(),
        library: library.to_path_buf(),
        last_played,
        playtime_min,
    })
}

fn load_games() -> Result<Vec<Game>> {
    let root = find_steam_root()?;
    let libs = find_library_roots(&root)?;
    let play = load_play_records(&root)?;
    let mut games = Vec::new();
    for lib in &libs {
        let sa = lib.join("steamapps");
        for e in fs::read_dir(&sa)?.flatten() {
            let p = e.path();
            let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if !name.starts_with("appmanifest_") || !name.ends_with(".acf") { continue; }
            match parse_acf(&p, lib, &play) {
                Ok(g) if !is_tool(&g) => games.push(g),
                _ => {}
            }
        }
    }
    Ok(games)
}

// ── Sorting ───────────────────────────────────────────────────────────────────

#[derive(ValueEnum, Clone, PartialEq, Default)]
enum Sort { #[default] Score, Size, Date, Playtime, Name }

impl fmt::Display for Sort {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Sort::Score => write!(f, "Score"),
            Sort::Size => write!(f, "Size"),
            Sort::Date => write!(f, "Date"),
            Sort::Playtime => write!(f, "Playtime"),
            Sort::Name => write!(f, "Name"),
        }
    }
}

// ── TUI ───────────────────────────────────────────────────────────────────────

#[derive(PartialEq)]
enum InputMode { Normal, Filter }

struct TuiApp {
    all_games: Vec<Game>,
    visible: Vec<usize>,      // indices into all_games, sorted + filtered
    selected: HashSet<usize>, // game indices of checked items
    table_state: TableState,
    sort_by: Sort,
    sort_desc: bool,
    filter: String,
    mode: InputMode,
    goal_gib: Option<f64>,
}

impl TuiApp {
    fn new(games: Vec<Game>, goal_gib: Option<f64>) -> Self {
        let n = games.len();
        let mut app = Self {
            all_games: games,
            visible: (0..n).collect(),
            selected: HashSet::new(),
            table_state: TableState::default(),
            sort_by: Sort::Score,
            sort_desc: true,
            filter: String::new(),
            mode: InputMode::Normal,
            goal_gib,
        };
        app.apply();
        app.table_state.select(Some(0));
        app
    }

    // Greedy: pick highest-scored visible unselected games until goal is reached.
    fn auto_fill(&mut self) {
        let Some(goal) = self.goal_gib else { return };
        let mut needed = goal - self.total_gib();
        if needed <= 0.0 { return }
        for &gi in &self.visible.clone() {
            if self.selected.contains(&gi) { continue }
            self.selected.insert(gi);
            needed -= self.all_games[gi].size_gib();
            if needed <= 0.0 { break }
        }
    }

    fn apply(&mut self) {
        let filter = self.filter.to_lowercase();
        let mut vis: Vec<usize> = (0..self.all_games.len())
            .filter(|&i| self.all_games[i].name.to_lowercase().contains(&filter))
            .collect();
        let desc = self.sort_desc;
        match self.sort_by {
            Sort::Score    => vis.sort_by(|&a, &b| {
                let c = self.all_games[a].score().partial_cmp(&self.all_games[b].score()).unwrap();
                if desc { c.reverse() } else { c }
            }),
            Sort::Size     => vis.sort_by(|&a, &b| {
                let c = self.all_games[a].size_bytes.cmp(&self.all_games[b].size_bytes);
                if desc { c.reverse() } else { c }
            }),
            Sort::Date     => vis.sort_by(|&a, &b| {
                // Ascending date = least-recently-played first (most stale)
                let c = self.all_games[a].last_played.cmp(&self.all_games[b].last_played);
                if desc { c } else { c.reverse() }
            }),
            Sort::Playtime => vis.sort_by(|&a, &b| {
                let c = self.all_games[a].playtime_min.cmp(&self.all_games[b].playtime_min);
                if desc { c.reverse() } else { c }
            }),
            Sort::Name     => vis.sort_by(|&a, &b| {
                let c = self.all_games[a].name.cmp(&self.all_games[b].name);
                if desc { c.reverse() } else { c }
            }),
        }
        self.visible = vis;
        // Keep cursor in bounds
        if let Some(i) = self.table_state.selected() {
            if i >= self.visible.len() && !self.visible.is_empty() {
                self.table_state.select(Some(self.visible.len() - 1));
            }
        }
    }

    fn set_sort(&mut self, s: Sort) {
        if discriminant(&self.sort_by) == discriminant(&s) {
            self.sort_desc = !self.sort_desc;
        } else {
            self.sort_by = s;
            self.sort_desc = true;
        }
        self.apply();
    }

    fn move_cursor(&mut self, delta: i32) {
        let n = self.visible.len();
        if n == 0 { return; }
        let cur = self.table_state.selected().unwrap_or(0) as i32;
        self.table_state.select(Some((cur + delta).clamp(0, n as i32 - 1) as usize));
    }

    fn toggle(&mut self) {
        if let Some(vi) = self.table_state.selected() {
            if let Some(&gi) = self.visible.get(vi) {
                if !self.selected.remove(&gi) { self.selected.insert(gi); }
            }
        }
    }

    fn toggle_all(&mut self) {
        let all_on = self.visible.iter().all(|i| self.selected.contains(i));
        if all_on {
            for i in &self.visible { self.selected.remove(i); }
        } else {
            for &i in &self.visible { self.selected.insert(i); }
        }
    }

    fn selected_games(&self) -> Vec<Game> {
        let mut v: Vec<Game> = self.selected.iter()
            .map(|&i| self.all_games[i].clone())
            .collect();
        v.sort_by_key(|g| g.score() as u64);
        v.reverse();
        v
    }

    fn total_gib(&self) -> f64 {
        self.selected.iter().map(|&i| self.all_games[i].size_gib()).sum()
    }
}

fn render(f: &mut Frame, app: &mut TuiApp) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(5), Constraint::Length(4)])
        .split(f.area());

    // ── Table ──
    let dir = if app.sort_desc { "▼" } else { "▲" };
    let sort_label = format!("Sort: {}{dir}", app.sort_by);
    let title = format!(" steam-clean  [{sort_label}]  {}/{} games ", app.visible.len(), app.all_games.len());

    let header_style = Style::default().add_modifier(Modifier::BOLD).fg(Color::Cyan);
    let header = Row::new(vec![
        Cell::from(" "),
        Cell::from("#"),
        Cell::from("Name"),
        Cell::from("Size"),
        Cell::from("Last Played"),
        Cell::from("Playtime"),
        Cell::from("Score"),
    ]).style(header_style).height(1);

    let rows: Vec<Row> = app.visible.iter().enumerate().map(|(vi, &gi)| {
        let g = &app.all_games[gi];
        let checked = app.selected.contains(&gi);
        let base_style = if checked {
            Style::default().fg(Color::Green)
        } else {
            Style::default()
        };
        Row::new(vec![
            Cell::from(if checked { "[✓]" } else { "[ ]" }),
            Cell::from(format!("{}", vi + 1)),
            Cell::from(truncate(&g.name, 38).to_string()),
            Cell::from(format!("{:.1}G", g.size_gib())),
            Cell::from(g.last_played_str()),
            Cell::from(g.playtime_str()),
            Cell::from(format!("{:.0}", g.score())),
        ]).style(base_style)
    }).collect();

    let widths = [
        Constraint::Length(5),
        Constraint::Length(4),
        Constraint::Min(32),
        Constraint::Length(7),
        Constraint::Length(13),
        Constraint::Length(9),
        Constraint::Length(9),
    ];

    let table = Table::new(rows, widths)
        .header(header)
        .block(Block::default().borders(Borders::ALL).title(Span::raw(title)))
        .row_highlight_style(Style::default().bg(Color::DarkGray))
        .highlight_symbol("▶ ");

    f.render_stateful_widget(table, chunks[0], &mut app.table_state);

    // ── Footer ──
    let footer_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(1), Constraint::Length(1), Constraint::Length(1), Constraint::Length(1)])
        .split(chunks[1]);

    // Status line
    let current_gib = app.total_gib();
    let (status, status_style) = if let Some(goal) = app.goal_gib {
        let pct = (current_gib / goal * 100.0) as u32;
        if current_gib >= goal {
            (
                format!(" Selected: {}  |  {:.1} / {:.1} GiB  ✓ GOAL REACHED  ({}%)",
                    app.selected.len(), current_gib, goal, pct),
                Style::default().fg(Color::Green),
            )
        } else {
            let bar_w = 20usize;
            let filled = ((current_gib / goal).min(1.0) * bar_w as f64) as usize;
            let bar = format!("[{}{}]", "█".repeat(filled), "░".repeat(bar_w - filled));
            (
                format!(" Selected: {}  |  {:.1} / {:.1} GiB  {}  {}%  [t] auto-fill",
                    app.selected.len(), current_gib, goal, bar, pct),
                Style::default().fg(Color::Yellow),
            )
        }
    } else {
        (
            format!(" Selected: {} game(s)  |  {:.1} GiB to free", app.selected.len(), current_gib),
            Style::default().fg(Color::Yellow),
        )
    };
    f.render_widget(
        Paragraph::new(status).style(status_style),
        footer_chunks[0],
    );

    // Filter line
    let filter_line = if app.mode == InputMode::Filter {
        format!(" Filter: {}█", app.filter)
    } else if app.filter.is_empty() {
        " [/] to filter".into()
    } else {
        format!(" Filter: {}  ([/] to change, [ESC] to clear)", app.filter)
    };
    f.render_widget(
        Paragraph::new(filter_line).style(Style::default().fg(Color::Magenta)),
        footer_chunks[1],
    );

    // Key hints
    let hints = " [↑↓/jk] move  [SPACE] check  [a] all  [t] auto-fill to goal  [S]core [s]ize [d]ate [p]laytime [n]ame  [/] filter  [ENTER] confirm  [q] quit";
    f.render_widget(
        Paragraph::new(hints).style(Style::default().fg(Color::DarkGray)),
        footer_chunks[2],
    );
}

fn run_tui(games: Vec<Game>, goal_gib: Option<f64>) -> Result<Option<Vec<Game>>> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let mut terminal = Terminal::new(CrosstermBackend::new(stdout))?;

    let mut app = TuiApp::new(games, goal_gib);
    let result = (|| -> Result<Option<Vec<Game>>> {
        loop {
            terminal.draw(|f| render(f, &mut app))?;

            if !event::poll(Duration::from_millis(50))? { continue; }
            let Event::Key(key) = event::read()? else { continue; };

            match app.mode {
                InputMode::Filter => match key.code {
                    KeyCode::Esc => {
                        app.filter.clear();
                        app.mode = InputMode::Normal;
                        app.apply();
                    }
                    KeyCode::Enter => {
                        app.mode = InputMode::Normal;
                        app.apply();
                    }
                    KeyCode::Backspace => { app.filter.pop(); app.apply(); }
                    KeyCode::Char(c) => { app.filter.push(c); app.apply(); }
                    _ => {}
                },
                InputMode::Normal => match (key.modifiers, key.code) {
                    (_, KeyCode::Char('q'))
                    | (KeyModifiers::CONTROL, KeyCode::Char('c')) => return Ok(None),

                    (_, KeyCode::Enter) => {
                        return Ok(Some(app.selected_games()));
                    }

                    (_, KeyCode::Char('j')) | (_, KeyCode::Down) => app.move_cursor(1),
                    (_, KeyCode::Char('k')) | (_, KeyCode::Up) => app.move_cursor(-1),
                    (_, KeyCode::PageDown) => app.move_cursor(10),
                    (_, KeyCode::PageUp) => app.move_cursor(-10),
                    (_, KeyCode::Char('G')) => {
                        app.table_state.select(Some(app.visible.len().saturating_sub(1)));
                    }
                    (_, KeyCode::Char('g')) => app.table_state.select(Some(0)),

                    (_, KeyCode::Char(' ')) => app.toggle(),
                    (_, KeyCode::Char('a')) => app.toggle_all(),
                    (_, KeyCode::Char('t')) => app.auto_fill(),

                    (_, KeyCode::Char('S')) => app.set_sort(Sort::Score),
                    (_, KeyCode::Char('s')) => app.set_sort(Sort::Size),
                    (_, KeyCode::Char('d')) => app.set_sort(Sort::Date),
                    (_, KeyCode::Char('p')) => app.set_sort(Sort::Playtime),
                    (_, KeyCode::Char('n')) => app.set_sort(Sort::Name),

                    (_, KeyCode::Char('/')) => {
                        app.mode = InputMode::Filter;
                    }
                    (_, KeyCode::Esc) if !app.filter.is_empty() => {
                        app.filter.clear();
                        app.apply();
                    }
                    _ => {}
                },
            }
        }
    })();

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    result
}

// ── Uninstall ─────────────────────────────────────────────────────────────────

fn uninstall_force(game: &Game) -> Result<()> {
    let acf = game.library.join(format!("steamapps/appmanifest_{}.acf", game.appid));
    let dir = game.library.join("steamapps/common").join(&game.install_dir);
    if acf.exists() { fs::remove_file(&acf)?; }
    if dir.exists() { fs::remove_dir_all(&dir)?; }
    Ok(())
}

// ── CLI ───────────────────────────────────────────────────────────────────────

#[derive(Parser)]
#[command(name = "steam-clean", version, about = "Rank and remove Steam games by size × idle time")]
struct Cli {
    #[command(subcommand)]
    cmd: Option<Cmd>,
}

#[derive(Subcommand)]
enum Cmd {
    /// Print a ranked table to stdout (default)
    List {
        #[arg(short, long, default_value = "score")]
        sort: Sort,
        #[arg(long, help = "Only show games >= N GiB")]
        min_gib: Option<f64>,
    },
    /// Interactive TUI: browse, filter, select, and uninstall
    Tidy {
        /// Target GiB to free (e.g. 50, 50G, 50GiB); pre-selects games and shows progress
        #[arg(long, value_name = "SIZE")]
        goal: Option<String>,
    },
}

// ── Commands ──────────────────────────────────────────────────────────────────

fn cmd_list(mut games: Vec<Game>, sort: Sort, min_gib: Option<f64>) {
    if let Some(min) = min_gib { games.retain(|g| g.size_gib() >= min); }
    match sort {
        Sort::Score    => games.sort_by(|a, b| b.score().partial_cmp(&a.score()).unwrap()),
        Sort::Size     => games.sort_by(|a, b| b.size_bytes.cmp(&a.size_bytes)),
        Sort::Date     => games.sort_by(|a, b| a.last_played.cmp(&b.last_played)),
        Sort::Playtime => games.sort_by(|a, b| b.playtime_min.cmp(&a.playtime_min)),
        Sort::Name     => games.sort_by(|a, b| a.name.cmp(&b.name)),
    }
    let total: f64 = games.iter().map(|g| g.size_gib()).sum();
    println!(
        "{:<4}  {:<42}  {:>7}  {:>13}  {:>8}  {:>9}",
        "#", "NAME", "SIZE", "LAST PLAYED", "PLAYTIME", "SCORE"
    );
    println!("{}", "─".repeat(96));
    for (i, g) in games.iter().enumerate() {
        println!(
            "{:<4}  {:<42}  {:>6.1}G  {:>13}  {:>8}  {:>9.0}",
            i + 1,
            truncate(&g.name, 42),
            g.size_gib(),
            g.last_played_str(),
            g.playtime_str(),
            g.score(),
        );
    }
    println!("{}", "─".repeat(96));
    println!("  {} games  |  {total:.1} GiB total", games.len());
}

fn parse_gib(s: &str) -> Result<f64> {
    let s = s.trim().to_lowercase();
    let s = s.trim_end_matches("gib").trim_end_matches("gb").trim_end_matches('g').trim();
    s.parse::<f64>().with_context(|| format!("invalid size '{}' — expected e.g. 50, 50G, 50GiB", s))
}

fn cmd_tidy(games: Vec<Game>, goal: Option<String>) -> Result<()> {
    let goal_gib = goal.as_deref().map(parse_gib).transpose()?;

    let Some(selections) = run_tui(games, goal_gib)? else {
        println!("Aborted.");
        return Ok(());
    };

    if selections.is_empty() {
        println!("Nothing selected.");
        return Ok(());
    }

    let total_gib: f64 = selections.iter().map(|g| g.size_gib()).sum();
    println!("\nSelected {} game(s) — {total_gib:.1} GiB:", selections.len());
    for g in &selections {
        println!("  • {} ({:.1} GiB)", g.name, g.size_gib());
    }
    if let Some(goal) = goal_gib {
        let status = if total_gib >= goal { "✓ goal reached" } else { "under goal" };
        println!("  Goal: {goal:.1} GiB  |  {total_gib:.1} GiB selected  [{status}]");
    }

    print!("\nProceed? [y/N] ");
    io::stdout().flush()?;
    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    if input.trim().to_lowercase() != "y" {
        println!("Aborted.");
        return Ok(());
    }

    let total = selections.len();
    for (i, g) in selections.iter().enumerate() {
        print!("[{}/{}] {} ({:.1} GiB)... ", i + 1, total, g.name, g.size_gib());
        io::stdout().flush()?;
        match uninstall_force(g) {
            Ok(()) => println!("done"),
            Err(e) => println!("ERROR: {e}"),
        }
    }

    println!("\nDone — {total_gib:.1} GiB freed.");
    Ok(())
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let games = load_games().context("loading Steam library")?;
    if games.is_empty() { bail!("no installed games found"); }

    match cli.cmd.unwrap_or(Cmd::List { sort: Sort::Score, min_gib: None }) {
        Cmd::List { sort, min_gib } => cmd_list(games, sort, min_gib),
        Cmd::Tidy { goal } => cmd_tidy(games, goal)?,
    }
    Ok(())
}
