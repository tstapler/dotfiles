use std::path::Path;

use anyhow::{Context, Result};
use tree_sitter::Node;

/// Go's built-in primitive types worth flagging when two or more parameters share one.
/// Deliberately wider than the old ast-grep rule (which only covered
/// string/int/int32/int64/float32/float64/bool) — see
/// .claude/rules/primitive-obsession-checklist.md for the newtype/value-object fix.
const PRIMITIVE_TYPES: &[&str] = &[
    "string", "int", "int8", "int16", "int32", "int64", "uint", "uint8", "uint16", "uint32",
    "uint64", "float32", "float64", "bool", "byte", "rune",
];

#[derive(Debug, PartialEq, Eq)]
pub struct Finding {
    pub line: usize,
    pub message: String,
}

/// Detects two shapes of same-typed-parameter piles in Go function signatures:
///   (a) a single `parameter_declaration` naming ≥2 identifiers of one primitive
///       type, e.g. `func f(a, b string)`
///   (b) a run of ≥2 consecutive single-name `parameter_declaration`s that share
///       one primitive type, e.g. `func f(a string, b string)`
pub fn check_source(src: &str) -> Result<Vec<Finding>> {
    let mut parser = tree_sitter::Parser::new();
    parser
        .set_language(&tree_sitter_go::LANGUAGE.into())
        .context("loading tree-sitter-go grammar")?;
    let tree = parser
        .parse(src, None)
        .context("parsing Go source with tree-sitter")?;

    let mut findings = Vec::new();
    walk(tree.root_node(), src.as_bytes(), &mut findings);
    Ok(findings)
}

pub fn check_file(path: &Path) -> Result<Vec<Finding>> {
    let src = std::fs::read_to_string(path)
        .with_context(|| format!("reading {}", path.display()))?;
    check_source(&src)
}

fn walk(node: Node, src: &[u8], findings: &mut Vec<Finding>) {
    if node.kind() == "parameter_list" {
        check_parameter_list(node, src, findings);
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        walk(child, src, findings);
    }
}

struct Param<'a> {
    node: Node<'a>,
    name_count: usize,
    primitive_type: Option<&'a str>,
}

fn check_parameter_list<'a>(list: Node<'a>, src: &'a [u8], findings: &mut Vec<Finding>) {
    let mut cursor = list.walk();
    let params: Vec<Param<'a>> = list
        .children(&mut cursor)
        .filter(|n| n.kind() == "parameter_declaration")
        .map(|decl| describe_param(decl, src))
        .collect();

    // Case (a): one declaration naming multiple identifiers of one primitive type.
    for param in &params {
        if param.name_count >= 2 && let Some(ty) = param.primitive_type {
            findings.push(Finding {
                line: param.node.start_position().row + 1,
                message: format!(
                    "parameter declaration names {} identifiers of primitive type `{ty}` — consider a newtype/value object instead",
                    param.name_count
                ),
            });
        }
    }

    // Case (b): runs of ≥2 consecutive single-name declarations sharing a primitive type.
    let mut run_start = 0;
    while run_start < params.len() {
        let Some(ty) = single_name_primitive(&params[run_start]) else {
            run_start += 1;
            continue;
        };
        let mut run_end = run_start + 1;
        while run_end < params.len() && single_name_primitive(&params[run_end]) == Some(ty) {
            run_end += 1;
        }
        if run_end - run_start >= 2 {
            findings.push(Finding {
                line: params[run_start].node.start_position().row + 1,
                message: format!(
                    "{} consecutive parameters share primitive type `{ty}` — consider a newtype/value object instead",
                    run_end - run_start
                ),
            });
        }
        run_start = run_end;
    }
}

fn single_name_primitive<'a>(param: &Param<'a>) -> Option<&'a str> {
    if param.name_count == 1 {
        param.primitive_type
    } else {
        None
    }
}

fn describe_param<'a>(decl: Node<'a>, src: &'a [u8]) -> Param<'a> {
    let mut cursor = decl.walk();
    let name_count = decl.children_by_field_name("name", &mut cursor).count();

    let primitive_type = decl.child_by_field_name("type").and_then(|ty| {
        if ty.kind() == "type_identifier" {
            let text = ty.utf8_text(src).unwrap_or("");
            PRIMITIVE_TYPES.iter().find(|&&p| p == text).copied()
        } else {
            None
        }
    });

    Param {
        node: decl,
        name_count,
        primitive_type,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn flags_multi_name_declaration() {
        let findings = check_source("package main\nfunc f(a, b string) {}\n").unwrap();
        assert_eq!(findings.len(), 1);
        assert!(findings[0].message.contains("2 identifiers"));
    }

    #[test]
    fn flags_consecutive_single_name_declarations() {
        let findings =
            check_source("package main\nfunc f(a string, b string) {}\n").unwrap();
        assert_eq!(findings.len(), 1);
        assert!(findings[0].message.contains("2 consecutive parameters"));
    }

    #[test]
    fn flags_run_of_three() {
        let findings =
            check_source("package main\nfunc f(x int, y int, z int) {}\n").unwrap();
        assert_eq!(findings.len(), 1);
        assert!(findings[0].message.contains("3 consecutive parameters"));
    }

    #[test]
    fn allows_distinct_types() {
        let findings = check_source("package main\nfunc f(a string, b int) {}\n").unwrap();
        assert!(findings.is_empty());
    }

    #[test]
    fn allows_single_primitive_param() {
        let findings = check_source("package main\nfunc f(a string) {}\n").unwrap();
        assert!(findings.is_empty());
    }

    #[test]
    fn ignores_non_primitive_types() {
        let findings =
            check_source("package main\nfunc f(a MyType, b MyType) {}\n").unwrap();
        assert!(findings.is_empty());
    }

    #[test]
    fn does_not_double_count_across_run_and_multi_name() {
        // a, b string is one declaration (case a); c string is a separate single-name
        // declaration immediately after — together they'd also look like a run, but
        // case (a) already flagged the pair, so case (b) should not also fire since the
        // multi-name declaration itself isn't single-name and breaks the run.
        let findings =
            check_source("package main\nfunc f(a, b string, c string) {}\n").unwrap();
        assert_eq!(findings.len(), 1);
        assert!(findings[0].message.contains("2 identifiers"));
    }
}
