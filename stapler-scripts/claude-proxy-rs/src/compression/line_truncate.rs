//! Head/tail truncation for output that's still too long after the other
//! compressors have run: keep the first and last N lines and replace the
//! middle with an elision marker, mirroring rtk's `never_worse`-guarded caps
//! and tee-to-disk pattern (the full text is archived separately by the
//! caller — this module only decides what to keep inline).

/// If `text` has more than `head + tail` lines, keep the first `head` and
/// last `tail` lines and collapse the rest into a single marker line.
/// Returns the input unchanged otherwise.
pub fn truncate_lines(text: &str, head: usize, tail: usize) -> String {
    let lines: Vec<&str> = text.split('\n').collect();
    let keep = head + tail;
    if lines.len() <= keep {
        return text.to_string();
    }

    let omitted = lines.len() - keep;
    let mut out: Vec<String> = Vec::with_capacity(keep + 1);
    out.extend(lines[..head].iter().map(|l| l.to_string()));
    out.push(format!("[... {omitted} lines omitted ...]"));
    out.extend(lines[lines.len() - tail..].iter().map(|l| l.to_string()));
    out.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keeps_short_text_untouched() {
        let text = "a\nb\nc";
        assert_eq!(truncate_lines(text, 5, 5), text);
    }

    #[test]
    fn truncates_long_text() {
        let lines: Vec<String> = (0..100).map(|n| format!("line{n}")).collect();
        let text = lines.join("\n");
        let result = truncate_lines(&text, 10, 10);
        assert!(result.contains("line0"));
        assert!(result.contains("line9"));
        assert!(result.contains("line90"));
        assert!(result.contains("line99"));
        assert!(result.contains("[... 80 lines omitted ...]"));
        assert!(!result.contains("line50"));
    }

    #[test]
    fn boundary_exact_fit_untouched() {
        let lines: Vec<String> = (0..20).map(|n| format!("line{n}")).collect();
        let text = lines.join("\n");
        assert_eq!(truncate_lines(&text, 10, 10), text);
    }
}
