//! Common-prefix collapsing for path-heavy output (`grep -r`, `find`,
//! `ls -laR`): when most lines share a long leading directory path, print
//! that prefix once and strip it from every matching line instead of
//! repeating it on every row.

const MIN_LINES: usize = 5;
const MIN_PREFIX_LEN: usize = 8;
const MIN_MATCH_RATIO: f64 = 0.6;

/// Heuristic: is `text` dominated by lines carrying filesystem paths?
fn path_bearing_lines(lines: &[&str]) -> Vec<usize> {
    lines
        .iter()
        .enumerate()
        .filter(|(_, l)| l.contains('/') && !l.trim().is_empty())
        .map(|(i, _)| i)
        .collect()
}

/// Longest common prefix (ending on a `/` boundary) shared by `lines` at the
/// given indices.
fn longest_common_dir_prefix<'a>(lines: &[&'a str], indices: &[usize]) -> &'a str {
    if indices.is_empty() {
        return "";
    }
    let mut prefix = lines[indices[0]];
    for &idx in &indices[1..] {
        let line = lines[idx];
        let mut common = 0;
        for (a, b) in prefix.bytes().zip(line.bytes()) {
            if a != b {
                break;
            }
            common += 1;
        }
        // Two distinct multi-byte characters can share leading bytes before
        // diverging (e.g. box-drawing characters in `tree`-style output), so
        // the byte-level match point isn't guaranteed to land on a char
        // boundary in `prefix` — back off until it does before slicing.
        while common > 0 && !prefix.is_char_boundary(common) {
            common -= 1;
        }
        prefix = &prefix[..common];
        if prefix.is_empty() {
            return "";
        }
    }
    // Trim back to the last `/` so we never split a path segment in half.
    match prefix.rfind('/') {
        Some(pos) => &prefix[..=pos],
        None => "",
    }
}

/// Collapse a shared directory prefix across path-heavy lines. Returns the
/// input unchanged if no prefix meets the savings threshold.
pub fn collapse_common_prefix(text: &str) -> String {
    let lines: Vec<&str> = text.split('\n').collect();
    let candidates = path_bearing_lines(&lines);

    if lines.is_empty() || candidates.len() < MIN_LINES {
        return text.to_string();
    }
    if (candidates.len() as f64) < MIN_MATCH_RATIO * lines.len() as f64 {
        return text.to_string();
    }

    let prefix = longest_common_dir_prefix(&lines, &candidates);
    if prefix.len() < MIN_PREFIX_LEN {
        return text.to_string();
    }

    let mut out = Vec::with_capacity(lines.len() + 1);
    out.push(format!("[common path prefix: {prefix}]"));
    for (i, line) in lines.iter().enumerate() {
        if candidates.contains(&i) && line.starts_with(prefix) {
            out.push(format!("  {}", &line[prefix.len()..]));
        } else {
            out.push(line.to_string());
        }
    }

    let result = out.join("\n");
    if result.len() < text.len() {
        result
    } else {
        text.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn collapses_shared_prefix() {
        let text = "/Users/tstapler/dotfiles/src/a.rs:1:foo\n\
                     /Users/tstapler/dotfiles/src/b.rs:2:bar\n\
                     /Users/tstapler/dotfiles/src/c.rs:3:baz\n\
                     /Users/tstapler/dotfiles/src/d.rs:4:qux\n\
                     /Users/tstapler/dotfiles/src/e.rs:5:quux";
        let result = collapse_common_prefix(text);
        assert!(result.contains("[common path prefix: /Users/tstapler/dotfiles/src/]"));
        assert!(result.contains("a.rs:1:foo"));
        assert!(!result.contains("/Users/tstapler/dotfiles/src/a.rs"));
    }

    #[test]
    fn no_collapse_below_threshold() {
        let text = "a\nb\nc";
        assert_eq!(collapse_common_prefix(text), text);
    }

    #[test]
    fn no_collapse_when_paths_diverge() {
        let text = "/a/b/x.rs:1\n/c/d/y.rs:2\n/e/f/z.rs:3\n/g/h/w.rs:4\n/i/j/v.rs:5";
        assert_eq!(collapse_common_prefix(text), text);
    }

    #[test]
    fn does_not_panic_on_multibyte_divergence() {
        // Box-drawing characters share leading UTF-8 bytes before diverging
        // mid-character — the byte-level common-prefix scan must not stop at
        // a non-char-boundary offset when slicing.
        let text = "/repo/├── a.rs:1\n\
                     /repo/└── b.rs:2\n\
                     /repo/├── c.rs:3\n\
                     /repo/├── d.rs:4\n\
                     /repo/├── e.rs:5";
        // Must not panic; the exact collapsing behavior isn't the point here.
        let _ = collapse_common_prefix(text);
    }
}
