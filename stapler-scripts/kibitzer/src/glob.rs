use regex::Regex;

/// Convert a glob pattern (supporting `**`, `*`, `?`) into an anchored regex
/// matched against a `/`-separated relative path.
fn glob_to_regex(pattern: &str) -> Regex {
    let mut out = String::from("^");
    let mut chars = pattern.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '*' => {
                if chars.peek() == Some(&'*') {
                    chars.next();
                    // `**/` matches zero or more path segments; bare `**` matches anything.
                    if chars.peek() == Some(&'/') {
                        chars.next();
                        out.push_str("(.*/)?");
                    } else {
                        out.push_str(".*");
                    }
                } else {
                    out.push_str("[^/]*");
                }
            }
            '?' => out.push_str("[^/]"),
            '.' | '+' | '(' | ')' | '|' | '^' | '$' | '{' | '}' | '[' | ']' | '\\' => {
                out.push('\\');
                out.push(c);
            }
            other => out.push(other),
        }
    }
    out.push('$');
    Regex::new(&out).expect("glob_to_regex always produces a valid pattern")
}

/// Returns true if `rel_path` (relative to the repo root, `/`-separated) matches any
/// of the given glob patterns. An empty `scopes` list matches everything.
pub fn matches_scope(rel_path: &str, scopes: &[String]) -> bool {
    if scopes.is_empty() {
        return true;
    }
    scopes.iter().any(|pat| glob_to_regex(pat).is_match(rel_path))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matches_double_star_prefix() {
        assert!(matches_scope("server/services/foo.go", &["**/*.go".to_string()]));
        assert!(matches_scope("foo.go", &["**/*.go".to_string()]));
    }

    #[test]
    fn matches_exact_dir() {
        assert!(matches_scope(
            "web-app/src/components/Button.tsx",
            &["web-app/**/*.tsx".to_string()]
        ));
        assert!(!matches_scope(
            "server/main.go",
            &["web-app/**/*.tsx".to_string()]
        ));
    }

    #[test]
    fn empty_scope_matches_all() {
        assert!(matches_scope("anything/at/all.rs", &[]));
    }
}
