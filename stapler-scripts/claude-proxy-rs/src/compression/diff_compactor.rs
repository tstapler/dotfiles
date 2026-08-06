//! Diff-aware compaction for `git diff` / `git log -p` style unified-diff
//! output: drop boilerplate `index abc123..def456` lines and collapse long
//! runs of unchanged context lines within a hunk, while keeping every
//! added/removed line and all headers intact.

const CONTEXT_KEEP_EDGE: usize = 3;
const CONTEXT_COLLAPSE_THRESHOLD: usize = 8;

/// Heuristic: does `text` look like unified-diff output?
pub fn is_diff(text: &str) -> bool {
    text.lines().any(|l| l.starts_with("diff --git ") || l.starts_with("@@ "))
        && (text.contains("\n--- ") || text.starts_with("--- ") || text.contains("\n+++ "))
}

/// Compact unified-diff text. Never returns something longer than the input.
pub fn compact_diff(text: &str) -> String {
    let lines: Vec<&str> = text.split('\n').collect();
    let mut out: Vec<String> = Vec::with_capacity(lines.len());
    let mut i = 0;

    while i < lines.len() {
        let line = lines[i];

        // Boilerplate blob-hash line — carries no reviewable information.
        if line.starts_with("index ") && line.contains("..") {
            i += 1;
            continue;
        }

        // A run of unchanged context lines (leading single space, unified
        // diff convention) — collapse the middle if it's long.
        if is_context_line(line) {
            let start = i;
            let mut end = i;
            while end < lines.len() && is_context_line(lines[end]) {
                end += 1;
            }
            let run = &lines[start..end];
            if run.len() > CONTEXT_COLLAPSE_THRESHOLD {
                for l in &run[..CONTEXT_KEEP_EDGE] {
                    out.push(l.to_string());
                }
                out.push(format!(
                    "... [{} unchanged lines omitted] ...",
                    run.len() - 2 * CONTEXT_KEEP_EDGE
                ));
                for l in &run[run.len() - CONTEXT_KEEP_EDGE..] {
                    out.push(l.to_string());
                }
            } else {
                for l in run {
                    out.push(l.to_string());
                }
            }
            i = end;
            continue;
        }

        out.push(line.to_string());
        i += 1;
    }

    let result = out.join("\n");
    if result.len() < text.len() {
        result
    } else {
        text.to_string()
    }
}

/// A unified-diff context line has exactly one leading space (the diff
/// marker) before the original line's own content, which may itself start
/// with further whitespace — so any leading space marks a context line.
fn is_context_line(line: &str) -> bool {
    line.starts_with(' ')
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_diff(context_lines: usize) -> String {
        let mut s = String::from("diff --git a/foo.rs b/foo.rs\n");
        s.push_str("index 1111111..2222222 100644\n");
        s.push_str("--- a/foo.rs\n");
        s.push_str("+++ b/foo.rs\n");
        s.push_str("@@ -1,10 +1,10 @@\n");
        for n in 0..context_lines {
            s.push_str(&format!(" context line {n}\n"));
        }
        s.push_str("-old line\n");
        s.push_str("+new line\n");
        s
    }

    #[test]
    fn detects_diff() {
        let d = sample_diff(2);
        assert!(is_diff(&d));
        assert!(!is_diff("just some plain text\nwith no diff markers"));
    }

    #[test]
    fn drops_index_line() {
        let d = sample_diff(2);
        let compacted = compact_diff(&d);
        assert!(!compacted.contains("index 1111111"));
        assert!(compacted.contains("diff --git"));
        assert!(compacted.contains("-old line"));
        assert!(compacted.contains("+new line"));
    }

    #[test]
    fn collapses_long_context_run() {
        let d = sample_diff(20);
        let compacted = compact_diff(&d);
        assert!(compacted.contains("unchanged lines omitted"));
        assert!(compacted.contains("context line 0"));
        assert!(compacted.contains("context line 19"));
        assert!(!compacted.contains("context line 10"));
    }

    #[test]
    fn short_context_run_untouched() {
        let d = sample_diff(3);
        let compacted = compact_diff(&d);
        assert!(!compacted.contains("omitted"));
        assert!(compacted.contains("context line 0"));
        assert!(compacted.contains("context line 2"));
    }
}
