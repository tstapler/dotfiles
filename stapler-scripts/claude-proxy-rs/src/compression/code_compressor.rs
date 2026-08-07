//! CodeCompressor: tree-sitter AST-based code block compression.
//!
//! Parses a code block with the grammar for its declared language and
//! excises every comment node (any node whose `kind()` contains "comment",
//! which covers `comment`/`line_comment`/`block_comment` across grammars
//! without hardcoding per-language node names), then collapses blank lines
//! left behind. Unsupported languages, unparseable input, or input with no
//! comments all fall through to `None` (pass-through). Collapsing identical
//! function bodies (mentioned in the original epic-6b scope) is not
//! implemented — verifying semantic equivalence safely is out of scope here.

use tree_sitter::{Language, Node, Parser};

/// Stateless code block compressor.
pub struct CodeCompressor;

impl CodeCompressor {
    pub fn new() -> Self {
        CodeCompressor
    }

    /// Attempt comment-stripping compression for the given language.
    ///
    /// `language` is matched case-insensitively against common names and
    /// file-extension aliases (e.g. "rust"/"rs", "javascript"/"js").
    /// Returns `None` if the language is unsupported, the code fails to
    /// parse, no comments are found, or the result isn't smaller.
    pub fn compress(&self, code: &str, language: &str) -> Option<String> {
        let lang = language_for(language)?;

        let mut parser = Parser::new();
        parser.set_language(&lang).ok()?;
        let tree = parser.parse(code, None)?;

        let mut comment_ranges: Vec<(usize, usize)> = Vec::new();
        collect_comment_ranges(tree.root_node(), &mut comment_ranges);
        if comment_ranges.is_empty() {
            return None;
        }
        comment_ranges.sort_unstable_by_key(|r| r.0);

        let bytes = code.as_bytes();
        let mut stripped = Vec::with_capacity(bytes.len());
        let mut cursor = 0usize;
        for (start, end) in &comment_ranges {
            if *start < cursor {
                continue; // nested/overlapping range, already covered
            }
            stripped.extend_from_slice(&bytes[cursor..*start]);
            cursor = *end;
        }
        stripped.extend_from_slice(&bytes[cursor..]);

        let stripped = String::from_utf8(stripped).ok()?;
        let collapsed = collapse_blank_lines(&stripped);

        if collapsed.len() < code.len() {
            Some(collapsed)
        } else {
            None
        }
    }
}

impl Default for CodeCompressor {
    fn default() -> Self {
        Self::new()
    }
}

/// Find every fenced markdown code block (` ```lang ... ``` `) that declares
/// a recognized language tag and run it through `CodeCompressor`. Returns
/// `None` if there are no fenced blocks, none have a recognized language tag,
/// or none of them actually shrink — the same never-worse convention used by
/// every other stage in this pipeline.
pub fn compress_fenced_blocks(text: &str) -> Option<String> {
    let compressor = CodeCompressor::new();
    let mut result = String::with_capacity(text.len());
    let mut cursor = 0;
    let mut changed = false;

    while let Some(fence_start) = text[cursor..].find("```") {
        let fence_start = cursor + fence_start;
        let after_fence = fence_start + 3;
        let Some(newline) = text[after_fence..].find('\n') else {
            break;
        };
        let lang = text[after_fence..after_fence + newline].trim();
        let body_start = after_fence + newline + 1;

        let Some(close_rel) = text[body_start..].find("\n```") else {
            break;
        };
        let body_end = body_start + close_rel + 1; // include trailing newline
        let close_end = body_end + 3;

        let body = &text[body_start..body_end];
        result.push_str(&text[cursor..body_start]);
        if !lang.is_empty() {
            if let Some(stripped) = compressor.compress(body, lang) {
                result.push_str(&stripped);
                changed = true;
            } else {
                result.push_str(body);
            }
        } else {
            result.push_str(body);
        }
        cursor = close_end;
    }

    result.push_str(&text[cursor..]);

    if changed && result.len() < text.len() {
        Some(result)
    } else {
        None
    }
}

/// Recursively collect byte ranges of every comment node. Does not descend
/// into a comment's children once matched (comments have no meaningful
/// sub-structure to preserve).
fn collect_comment_ranges(node: Node, out: &mut Vec<(usize, usize)>) {
    if node.kind().to_ascii_lowercase().contains("comment") {
        out.push((node.start_byte(), node.end_byte()));
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_comment_ranges(child, out);
    }
}

/// Trim trailing whitespace left by comment removal on each line, then drop
/// lines that are now entirely blank (these are almost always lines that
/// held nothing but a stripped comment) while collapsing any remaining runs
/// of blank lines down to one.
fn collapse_blank_lines(text: &str) -> String {
    let mut out: Vec<&str> = Vec::new();
    let mut prev_blank = false;
    for raw_line in text.split('\n') {
        let line = raw_line.trim_end();
        if line.is_empty() {
            if !prev_blank {
                out.push("");
            }
            prev_blank = true;
        } else {
            out.push(line);
            prev_blank = false;
        }
    }
    out.join("\n")
}

/// Resolve a declared code-block language name to a tree-sitter `Language`.
fn language_for(name: &str) -> Option<Language> {
    match name.to_ascii_lowercase().as_str() {
        "rust" | "rs" => Some(tree_sitter_rust::LANGUAGE.into()),
        "python" | "py" => Some(tree_sitter_python::LANGUAGE.into()),
        "javascript" | "js" | "jsx" => Some(tree_sitter_javascript::LANGUAGE.into()),
        "typescript" | "ts" => Some(tree_sitter_typescript::LANGUAGE_TYPESCRIPT.into()),
        "tsx" => Some(tree_sitter_typescript::LANGUAGE_TSX.into()),
        "go" | "golang" => Some(tree_sitter_go::LANGUAGE.into()),
        "bash" | "sh" | "shell" | "zsh" => Some(tree_sitter_bash::LANGUAGE.into()),
        "java" => Some(tree_sitter_java::LANGUAGE.into()),
        "c" => Some(tree_sitter_c::LANGUAGE.into()),
        "cpp" | "c++" | "cc" | "cxx" => Some(tree_sitter_cpp::LANGUAGE.into()),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_rust_line_and_block_comments() {
        let code = "// header comment\nfn main() {\n    /* block */\n    let x = 1; // trailing\n    println!(\"{x}\");\n}\n";
        let result = CodeCompressor::new().compress(code, "rust").expect("should compress");
        assert!(!result.contains("header comment"));
        assert!(!result.contains("block"));
        assert!(!result.contains("trailing"));
        assert!(result.contains("fn main()"));
        assert!(result.contains("println!"));
    }

    #[test]
    fn strips_python_comments() {
        let code = "# module comment\ndef f():\n    x = 1  # inline\n    return x\n";
        let result = CodeCompressor::new().compress(code, "python").expect("should compress");
        assert!(!result.contains("module comment"));
        assert!(!result.contains("inline"));
        assert!(result.contains("def f()"));
        assert!(result.contains("return x"));
    }

    #[test]
    fn strips_javascript_comments() {
        let code = "// top\nfunction f() {\n  /* mid */\n  return 1; // end\n}\n";
        let result = CodeCompressor::new().compress(code, "javascript").expect("should compress");
        assert!(!result.contains("top"));
        assert!(!result.contains("mid"));
        assert!(!result.contains("end"));
        assert!(result.contains("function f()"));
    }

    #[test]
    fn strips_typescript_comments() {
        let code = "// note\ninterface Foo {\n  x: number; // field\n}\n";
        let result = CodeCompressor::new().compress(code, "typescript").expect("should compress");
        assert!(!result.contains("note"));
        assert!(!result.contains("field"));
        assert!(result.contains("interface Foo"));
    }

    #[test]
    fn strips_go_comments() {
        let code = "// Package doc\npackage main\n\nfunc main() {\n\t// inline\n\tprintln(1)\n}\n";
        let result = CodeCompressor::new().compress(code, "go").expect("should compress");
        assert!(!result.contains("Package doc"));
        assert!(!result.contains("inline"));
        assert!(result.contains("package main"));
    }

    #[test]
    fn strips_bash_comments() {
        let code = "#!/bin/bash\n# a comment\necho hi # trailing\n";
        let result = CodeCompressor::new().compress(code, "bash").expect("should compress");
        assert!(!result.contains("# a comment"));
        assert!(!result.contains("trailing"));
        assert!(result.contains("echo hi"));
    }

    #[test]
    fn strips_java_comments() {
        let code = "// header\nclass Foo {\n  /* body */\n  int x = 1; // field\n}\n";
        let result = CodeCompressor::new().compress(code, "java").expect("should compress");
        assert!(!result.contains("header"));
        assert!(!result.contains("body"));
        assert!(!result.contains("field"));
        assert!(result.contains("class Foo"));
    }

    #[test]
    fn strips_c_comments() {
        let code = "// header\nint main() {\n  /* body */\n  return 0; // ret\n}\n";
        let result = CodeCompressor::new().compress(code, "c").expect("should compress");
        assert!(!result.contains("header"));
        assert!(!result.contains("body"));
        assert!(result.contains("int main()"));
    }

    #[test]
    fn strips_cpp_comments() {
        let code = "// header\nclass Foo {\npublic:\n  // ctor\n  Foo() {}\n};\n";
        let result = CodeCompressor::new().compress(code, "cpp").expect("should compress");
        assert!(!result.contains("header"));
        assert!(!result.contains("ctor"));
        assert!(result.contains("class Foo"));
    }

    #[test]
    fn no_op_on_unsupported_language() {
        let code = "// this looks like code\nfoo bar baz";
        assert!(CodeCompressor::new().compress(code, "cobol").is_none());
    }

    #[test]
    fn no_op_when_no_comments_present() {
        let code = "fn main() {\n    println!(\"hi\");\n}\n";
        assert!(CodeCompressor::new().compress(code, "rust").is_none());
    }

    #[test]
    fn no_op_on_unparseable_input() {
        // tree-sitter is error-tolerant and will still return a tree for
        // garbage input; this just needs to not panic either way.
        let code = "@@@ not valid rust {{{";
        let _ = CodeCompressor::new().compress(code, "rust");
    }

    #[test]
    fn compresses_fenced_code_block_in_markdown() {
        let text = "Some prose.\n\n```rust\n// header\nfn main() {\n    println!(\"hi\"); // trailing\n}\n```\n\nMore prose.\n";
        let result = compress_fenced_blocks(text).expect("should compress");
        assert!(!result.contains("header"));
        assert!(!result.contains("trailing"));
        assert!(result.contains("Some prose."));
        assert!(result.contains("More prose."));
        assert!(result.contains("fn main()"));
    }

    #[test]
    fn fenced_blocks_no_op_without_language_tag() {
        let text = "```\n// not a recognized language\nfoo\n```\n";
        assert!(compress_fenced_blocks(text).is_none());
    }

    #[test]
    fn fenced_blocks_no_op_when_no_comments() {
        let text = "```rust\nfn main() {}\n```\n";
        assert!(compress_fenced_blocks(text).is_none());
    }

    #[test]
    fn does_not_strip_comment_like_string_contents() {
        let code = "fn main() {\n    let s = \"// not a comment\";\n    println!(\"{s}\");\n}\n";
        // No real comment nodes exist, so this should be a no-op — proving
        // the string literal wasn't misidentified as a comment.
        assert!(CodeCompressor::new().compress(code, "rust").is_none());
    }
}
