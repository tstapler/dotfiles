//! Native text compressor: ANSI strip, log dedup, blank line normalization.
//!
//! Ports the observable compression behaviors from `compactor.py` / FusionEngine
//! for plain text content blocks.  Operates entirely on `&str` → `String`.

use once_cell::sync::Lazy;
use regex::Regex;

/// Matches ANSI terminal escape sequences (colors, cursor movement, erase).
static ANSI_ESCAPE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\x1b\[[0-9;]*[mK]").expect("ANSI_ESCAPE regex"));

/// Matches an ISO 8601 timestamp embedded in a log line.
/// Captures the prefix before, the timestamp itself, and the suffix after.
static ISO_TIMESTAMP: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")
        .expect("ISO_TIMESTAMP regex")
});

/// Stateless text compressor.
pub struct TextCompressor;

impl TextCompressor {
    pub fn new() -> Self {
        TextCompressor
    }

    /// Apply all compression transforms to `text` and return the result.
    ///
    /// If the result would be longer than the input, the original is returned
    /// unchanged.
    pub fn compress(&self, text: &str) -> String {
        let s = strip_ansi(text);
        let s = dedup_consecutive_lines(&s);
        let s = normalize_blank_lines(&s);
        let s = dedup_log_timestamps(&s);

        // Safety net: never return something longer than the input.
        if s.len() < text.len() {
            s
        } else {
            text.to_string()
        }
    }
}

impl Default for TextCompressor {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Transform helpers
// ---------------------------------------------------------------------------

/// Remove ANSI escape sequences.
fn strip_ansi(text: &str) -> String {
    ANSI_ESCAPE.replace_all(text, "").into_owned()
}

/// Deduplicate consecutive identical lines.
///
/// When 3 or more identical non-blank lines appear in a row, replace them with:
///   `<line>\n[N more identical lines]`
/// where N = count - 1.
fn dedup_consecutive_lines(text: &str) -> String {
    let lines: Vec<&str> = text.split('\n').collect();
    if lines.is_empty() {
        return text.to_string();
    }

    let mut out: Vec<String> = Vec::with_capacity(lines.len());
    let mut i = 0;

    while i < lines.len() {
        let current = lines[i];

        // Don't collapse blank/whitespace-only lines here; handled separately.
        if current.trim().is_empty() {
            out.push(current.to_string());
            i += 1;
            continue;
        }

        // Count consecutive occurrences of this line.
        let mut count = 1;
        while i + count < lines.len() && lines[i + count] == current {
            count += 1;
        }

        if count >= 3 {
            out.push(current.to_string());
            out.push(format!("[{} more identical lines]", count - 1));
        } else {
            for _ in 0..count {
                out.push(current.to_string());
            }
        }

        i += count;
    }

    out.join("\n")
}

/// Collapse 3 or more consecutive blank lines down to 2 blank lines.
fn normalize_blank_lines(text: &str) -> String {
    let lines: Vec<&str> = text.split('\n').collect();
    let mut out: Vec<String> = Vec::with_capacity(lines.len());
    let mut blank_run: usize = 0;

    for line in &lines {
        if line.trim().is_empty() {
            blank_run += 1;
            if blank_run <= 1 {
                out.push(line.to_string());
            }
            // If blank_run > 1, skip the line (collapse to at most one blank line).
        } else {
            blank_run = 0;
            out.push(line.to_string());
        }
    }

    out.join("\n")
}

/// Replace repeated log lines (lines containing ISO 8601 timestamps) with a
/// summary when the same pattern (timestamp replaced by `{timestamp}`) repeats
/// 3 or more times.
fn dedup_log_timestamps(text: &str) -> String {
    let lines: Vec<&str> = text.split('\n').collect();
    if lines.is_empty() {
        return text.to_string();
    }

    // Build a list of (original_line, pattern) pairs.
    // Pattern = line with any ISO timestamp replaced by `{timestamp}`.
    let annotated: Vec<(&str, String)> = lines
        .iter()
        .map(|&line| {
            let pattern = ISO_TIMESTAMP.replace_all(line, "{timestamp}").into_owned();
            (line, pattern)
        })
        .collect();

    let mut out: Vec<String> = Vec::with_capacity(lines.len());
    let mut i = 0;

    while i < annotated.len() {
        let (line, pattern) = &annotated[i];

        // Only apply dedup to lines that actually contain a timestamp.
        if !ISO_TIMESTAMP.is_match(line) {
            out.push(line.to_string());
            i += 1;
            continue;
        }

        // Count consecutive lines with the same pattern.
        let mut count = 1;
        while i + count < annotated.len() && annotated[i + count].1 == *pattern {
            count += 1;
        }

        if count >= 3 {
            out.push(line.to_string());
            out.push(format!("[{} more identical log lines]", count - 1));
        } else {
            for j in 0..count {
                out.push(annotated[i + j].0.to_string());
            }
        }

        i += count;
    }

    out.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_ansi() {
        let input = "\x1b[31mred\x1b[0m normal";
        assert_eq!(strip_ansi(input), "red normal");
    }

    #[test]
    fn dedup_three_identical_lines() {
        let input = "foo\nfoo\nfoo\nbar";
        let result = dedup_consecutive_lines(input);
        assert!(result.contains("[2 more identical lines]"));
        assert!(!result.contains("foo\nfoo\nfoo"));
    }

    #[test]
    fn two_identical_lines_not_deduped() {
        let input = "foo\nfoo\nbar";
        let result = dedup_consecutive_lines(input);
        assert_eq!(result, "foo\nfoo\nbar");
    }

    #[test]
    fn blank_line_normalization() {
        let input = "a\n\n\n\n\nb";
        let result = normalize_blank_lines(input);
        // Should have at most 2 consecutive blank lines.
        assert!(!result.contains("\n\n\n"));
    }

    #[test]
    fn log_timestamp_dedup() {
        let input = "2024-01-15T10:23:45.123Z INFO starting\n\
                     2024-01-15T10:23:46.456Z INFO starting\n\
                     2024-01-15T10:23:47.789Z INFO starting\n\
                     done";
        let result = dedup_log_timestamps(input);
        assert!(result.contains("[2 more identical log lines]"));
    }

    #[test]
    fn compress_noop_on_short_text() {
        let c = TextCompressor::new();
        let short = "hello world";
        assert_eq!(c.compress(short), short);
    }
}
