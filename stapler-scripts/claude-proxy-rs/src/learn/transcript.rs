//! JSONL transcript parser for `~/.claude/projects/`.
//!
//! The Claude Code transcript format has no official spec and the schema is
//! subject to change without notice. This parser is intentionally defensive:
//! - Unknown top-level `type` values are silently skipped.
//! - Lines that fail to deserialize are silently skipped.
//! - `message.content` is treated as either a plain `String` or a
//!   `Vec<ContentBlock>` (serde untagged enum).
//! - Entries where `isSidechain == true` are skipped (sub-agent messages).
//! - Entries where `isMeta == true` are skipped.
//! - Only `type == "user"` entries with plain-string content are useful for
//!   correction-pattern matching.

use anyhow::Result;
use glob::glob;
use serde::Deserialize;
use std::path::PathBuf;
use tracing::debug;

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/// A single entry from a Claude Code JSONL transcript file.
#[derive(Debug, Clone)]
pub struct TranscriptEntry {
    pub uuid: String,
    pub parent_uuid: Option<String>,
    /// "user" or "assistant"
    pub role: String,
    /// Plain text content (non-text blocks are skipped; empty if no text)
    pub content: String,
    pub is_sidechain: bool,
    pub is_meta: bool,
    /// The session JSONL file this entry came from
    pub session_path: PathBuf,
}

// ---------------------------------------------------------------------------
// Internal serde types (schema is unstable — use permissive deserialization)
// ---------------------------------------------------------------------------

/// Raw deserialized form of a single JSONL line.
///
/// All fields are `Option` so unknown structure gracefully produces `None`
/// rather than a deserialisation error. Unknown top-level fields are ignored
/// via the default serde behaviour (no `deny_unknown_fields`).
#[derive(Debug, Deserialize)]
struct RawEntry {
    #[serde(rename = "type")]
    entry_type: Option<String>,

    uuid: Option<String>,

    #[serde(rename = "parentUuid")]
    parent_uuid: Option<String>,

    #[serde(rename = "isSidechain", default)]
    is_sidechain: bool,

    #[serde(rename = "isMeta", default)]
    is_meta: bool,

    message: Option<RawMessage>,
}

#[derive(Debug, Deserialize)]
struct RawMessage {
    role: Option<String>,
    content: Option<RawContent>,
}

/// `message.content` is either a plain string or an array of content blocks.
#[derive(Debug, Deserialize)]
#[serde(untagged)]
enum RawContent {
    Text(String),
    Blocks(Vec<RawContentBlock>),
}

#[derive(Debug, Deserialize)]
struct RawContentBlock {
    #[serde(rename = "type")]
    block_type: Option<String>,
    text: Option<String>,
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Parse all JSONL transcripts under `~/.claude/projects/**/*.jsonl` and
/// return all entries ordered by appearance in file.
///
/// Silently skips files that cannot be opened and lines that fail to
/// deserialise (the schema is unstable).
pub fn parse_all_transcripts() -> Result<Vec<TranscriptEntry>> {
    let home = dirs_home()?;
    let pattern = format!("{}/.claude/projects/**/*.jsonl", home.display());
    parse_transcripts_glob(&pattern)
}

/// Parse transcripts matching an arbitrary glob pattern.
///
/// Exposed separately so tests can point at fixture directories.
pub fn parse_transcripts_glob(pattern: &str) -> Result<Vec<TranscriptEntry>> {
    let mut all = Vec::new();

    for path_result in glob(pattern).map_err(|e| anyhow::anyhow!("glob error: {}", e))? {
        match path_result {
            Ok(path) => {
                let entries = parse_file(&path);
                debug!(path = %path.display(), count = entries.len(), "parsed transcript");
                all.extend(entries);
            }
            Err(e) => {
                debug!("glob entry error: {}", e);
            }
        }
    }

    Ok(all)
}

/// Parse a single JSONL file, returning `TranscriptEntry` values.
///
/// Lines that fail to deserialise are silently skipped.
pub fn parse_file(path: &PathBuf) -> Vec<TranscriptEntry> {
    let content = match std::fs::read_to_string(path) {
        Ok(c) => c,
        Err(e) => {
            debug!(path = %path.display(), error = %e, "failed to read transcript file");
            return Vec::new();
        }
    };

    let mut entries = Vec::new();

    for (line_num, line) in content.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }

        let raw: RawEntry = match serde_json::from_str(line) {
            Ok(r) => r,
            Err(e) => {
                debug!(
                    path = %path.display(),
                    line = line_num + 1,
                    error = %e,
                    "skipping unparseable line"
                );
                continue;
            }
        };

        // Only process "user" and "assistant" entries.
        let entry_role = match raw.entry_type.as_deref() {
            Some("user") => "user",
            Some("assistant") => "assistant",
            _ => continue,
        };

        // Skip sidechain (sub-agent) entries.
        if raw.is_sidechain {
            continue;
        }

        let message = match &raw.message {
            Some(m) => m,
            None => continue,
        };

        let role = message
            .role
            .as_deref()
            .unwrap_or(entry_role)
            .to_string();

        let content = extract_plain_text_content(&message.content);
        if content.is_empty() {
            continue;
        }

        entries.push(TranscriptEntry {
            uuid: raw.uuid.unwrap_or_default(),
            parent_uuid: raw.parent_uuid,
            role,
            content,
            is_sidechain: raw.is_sidechain,
            is_meta: raw.is_meta,
            session_path: path.clone(),
        });
    }

    entries
}

/// Extract plain text from a `RawContent`.
///
/// - Plain `String` → returned as-is.
/// - `Vec<ContentBlock>` → concatenate only `type == "text"` blocks with
///   `"\n"` separator; skip `tool_use`, `tool_result`, `image`, `thinking`.
fn extract_plain_text_content(content: &Option<RawContent>) -> String {
    match content {
        None => String::new(),
        Some(RawContent::Text(s)) => s.clone(),
        Some(RawContent::Blocks(blocks)) => {
            let texts: Vec<&str> = blocks
                .iter()
                .filter(|b| b.block_type.as_deref() == Some("text"))
                .filter_map(|b| b.text.as_deref())
                .collect();
            texts.join("\n")
        }
    }
}

/// Resolve the user's home directory from the `HOME` environment variable.
fn dirs_home() -> Result<PathBuf> {
    std::env::var("HOME")
        .map(PathBuf::from)
        .map_err(|_| anyhow::anyhow!("HOME environment variable not set"))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn write_temp_jsonl(lines: &[&str]) -> NamedTempFile {
        let mut f = NamedTempFile::new().unwrap();
        for line in lines {
            writeln!(f, "{}", line).unwrap();
        }
        f
    }

    #[test]
    fn test_parse_plain_string_user_message() {
        let f = write_temp_jsonl(&[
            r#"{"type":"user","uuid":"abc","parentUuid":null,"isSidechain":false,"isMeta":false,"message":{"role":"user","content":"no, don't do that"}}"#,
        ]);
        let entries = parse_file(&f.path().to_path_buf());
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].content, "no, don't do that");
        assert_eq!(entries[0].role, "user");
        assert!(!entries[0].is_sidechain);
    }

    #[test]
    fn test_skip_sidechain_entries() {
        let f = write_temp_jsonl(&[
            r#"{"type":"user","uuid":"sid","parentUuid":null,"isSidechain":true,"isMeta":false,"message":{"role":"user","content":"subagent message"}}"#,
        ]);
        let entries = parse_file(&f.path().to_path_buf());
        assert_eq!(entries.len(), 0);
    }

    #[test]
    fn test_skip_unknown_type() {
        let f = write_temp_jsonl(&[
            r#"{"type":"ai-title","uuid":"t1","message":{"role":"user","content":"title"}}"#,
            r#"{"type":"user","uuid":"t2","isSidechain":false,"isMeta":false,"message":{"role":"user","content":"real message"}}"#,
        ]);
        let entries = parse_file(&f.path().to_path_buf());
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].content, "real message");
    }

    #[test]
    fn test_array_content_extracts_text_blocks_only() {
        let f = write_temp_jsonl(&[
            r#"{"type":"user","uuid":"u1","isSidechain":false,"isMeta":false,"message":{"role":"user","content":[{"type":"text","text":"hello"},{"type":"tool_result","tool_use_id":"xyz","content":"result"},{"type":"text","text":"world"}]}}"#,
        ]);
        let entries = parse_file(&f.path().to_path_buf());
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].content, "hello\nworld");
    }

    #[test]
    fn test_silently_skip_malformed_lines() {
        let f = write_temp_jsonl(&[
            "not json at all {{{",
            r#"{"type":"user","uuid":"ok","isSidechain":false,"isMeta":false,"message":{"role":"user","content":"valid"}}"#,
        ]);
        let entries = parse_file(&f.path().to_path_buf());
        assert_eq!(entries.len(), 1);
    }

    #[test]
    fn test_assistant_entries_included() {
        let f = write_temp_jsonl(&[
            r#"{"type":"assistant","uuid":"a1","isSidechain":false,"isMeta":false,"message":{"role":"assistant","content":[{"type":"text","text":"here is my response"}]}}"#,
        ]);
        let entries = parse_file(&f.path().to_path_buf());
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].role, "assistant");
    }

    #[test]
    fn test_empty_array_content_skipped() {
        // A user message with only tool_result blocks (no text) -> content is
        // empty -> entry is skipped.
        let f = write_temp_jsonl(&[
            r#"{"type":"user","uuid":"tr","isSidechain":false,"isMeta":false,"message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"t1","content":"result"}]}}"#,
        ]);
        let entries = parse_file(&f.path().to_path_buf());
        assert_eq!(entries.len(), 0);
    }

    #[test]
    fn test_parent_uuid_preserved() {
        let f = write_temp_jsonl(&[
            r#"{"type":"user","uuid":"child","parentUuid":"parent-uuid","isSidechain":false,"isMeta":false,"message":{"role":"user","content":"follow-up"}}"#,
        ]);
        let entries = parse_file(&f.path().to_path_buf());
        assert_eq!(entries[0].parent_uuid, Some("parent-uuid".to_string()));
    }
}
