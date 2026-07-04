//! Schema compression for `tools/list` responses.
//!
//! Reduces token count by truncating descriptions and stripping verbose JSON Schema
//! fields, while preserving correctness of `tools/call` invocations.
//!
//! Compression levels (from `config::CompressionLevel`):
//! - `Off`        — no transformation
//! - `Light`      — description truncated to first sentence (max 200 chars)
//! - `Aggressive` — Light + `examples` stripped + `$ref` inlined + `title` removed from schemas

use std::collections::{HashMap, HashSet};
use std::sync::Arc;

use rmcp::model::Tool;
use serde_json::{Map, Value};

use crate::config::CompressionLevel;

pub struct SchemaCompressor {
    level: CompressionLevel,
}

impl SchemaCompressor {
    pub fn new(level: CompressionLevel) -> Self {
        Self { level }
    }

    /// Apply compression to a tool list. Returns the list unchanged for `Off`.
    pub fn compress(&self, tools: Vec<Tool>) -> Vec<Tool> {
        match self.level {
            CompressionLevel::Off => tools,
            CompressionLevel::Light => tools.into_iter().map(|t| self.compress_light(t)).collect(),
            CompressionLevel::Aggressive => {
                tools.into_iter().map(|t| self.compress_aggressive(t)).collect()
            }
        }
    }

    // ── Light ─────────────────────────────────────────────────────────────────

    fn compress_light(&self, mut tool: Tool) -> Tool {
        tool.description = tool
            .description
            .as_deref()
            .map(|d| first_sentence(d, 200))
            .map(|s| std::borrow::Cow::Owned(s.to_string()));
        tool
    }

    // ── Aggressive ────────────────────────────────────────────────────────────

    fn compress_aggressive(&self, mut tool: Tool) -> Tool {
        tool.description = tool
            .description
            .as_deref()
            .map(|d| first_sentence(d, 200))
            .map(|s| std::borrow::Cow::Owned(s.to_string()));

        // Extract $defs for $ref resolution, then rebuild a flat schema
        let schema = Arc::try_unwrap(tool.input_schema)
            .unwrap_or_else(|arc| (*arc).clone());
        tool.input_schema = Arc::new(compress_schema_aggressive(schema));
        tool
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Return the first sentence of a description, capped at `max_chars`.
///
/// A "sentence" ends at `. `, `.\n`, `\n\n`, or the string boundary.
/// Trailing punctuation from the split is dropped.
fn first_sentence(text: &str, max_chars: usize) -> &str {
    let text = text.trim();
    // First paragraph
    let para = match text.find("\n\n") {
        Some(i) => &text[..i],
        None => text,
    };
    // First line of the paragraph
    let line = match para.find('\n') {
        Some(i) => &para[..i],
        None => para,
    }
    .trim();
    // First sentence of the line (split on ". " or ".\n", keep up to the dot)
    let sentence = match line.find(". ") {
        Some(i) => &line[..i],
        None => line,
    };
    let result = sentence.trim_end_matches('.');
    // Cap at max_chars (character boundary)
    let cap = result
        .char_indices()
        .nth(max_chars)
        .map(|(i, _)| i)
        .unwrap_or(result.len());
    &result[..cap]
}

// ── Aggressive schema transformation ─────────────────────────────────────────

fn compress_schema_aggressive(mut schema: Map<String, Value>) -> Map<String, Value> {
    // Collect $defs (JSON Schema §8.2.1) for $ref resolution
    let defs: HashMap<String, Value> = extract_defs(&schema);
    schema.remove("$defs");
    schema.remove("definitions"); // legacy keyword alias

    // Inline $refs and strip examples/title throughout
    inline_and_strip(&mut schema, &defs, 0);

    schema
}

/// Pull the definitions map out of the schema without consuming the original.
fn extract_defs(schema: &Map<String, Value>) -> HashMap<String, Value> {
    let mut defs = HashMap::new();
    for key in &["$defs", "definitions"] {
        if let Some(Value::Object(map)) = schema.get(*key) {
            for (k, v) in map {
                defs.insert(k.clone(), v.clone());
            }
        }
    }
    defs
}

/// Recursively walk an object, inlining `$ref` pointers and stripping noise.
///
/// `depth` guards against cyclic schemas (max 3 levels of inlining).
fn inline_and_strip(
    obj: &mut Map<String, Value>,
    defs: &HashMap<String, Value>,
    depth: usize,
) {
    const MAX_DEPTH: usize = 3;

    // Inline $ref if present (replaces the whole object's contents)
    if let Some(Value::String(ref_path)) = obj.get("$ref").cloned() {
        if depth < MAX_DEPTH {
            if let Some(resolved) = resolve_ref(&ref_path, defs) {
                if let Value::Object(mut resolved_obj) = resolved {
                    // Strip $ref from the resolved object to avoid infinite loops
                    resolved_obj.remove("$ref");
                    // Merge resolved fields into obj, keeping non-ref fields already present
                    obj.remove("$ref");
                    for (k, v) in resolved_obj {
                        obj.entry(k).or_insert(v);
                    }
                    // Recurse on the now-inlined object
                    inline_and_strip(obj, defs, depth + 1);
                    return;
                }
            } else {
                // Unresolvable $ref: just remove it to avoid sending it to the model
                obj.remove("$ref");
            }
        } else {
            // Max depth: drop $ref rather than expanding further
            obj.remove("$ref");
        }
    }

    // Strip noise fields from this schema object
    obj.remove("examples");
    obj.remove("title");

    // Recurse into nested schemas.
    // `properties` and `patternProperties` hold parameter *names* as keys — do NOT
    // call inline_and_strip on the map itself or those keys would be stripped.
    // Instead, visit each parameter schema value directly.
    let keys: Vec<String> = obj.keys().cloned().collect();
    for key in keys {
        match key.as_str() {
            "properties" | "patternProperties" => {
                if let Some(Value::Object(props)) = obj.get_mut(&key) {
                    let prop_keys: Vec<String> = props.keys().cloned().collect();
                    for pk in prop_keys {
                        if let Some(Value::Object(param_schema)) = props.get_mut(&pk) {
                            inline_and_strip(param_schema, defs, depth);
                        }
                    }
                }
            }
            _ => match obj.get_mut(&key) {
                Some(Value::Object(child)) => {
                    inline_and_strip(child, defs, depth);
                }
                Some(Value::Array(arr)) => {
                    strip_array(arr, defs, depth);
                }
                _ => {}
            },
        }
    }
}

fn strip_array(arr: &mut Vec<Value>, defs: &HashMap<String, Value>, depth: usize) {
    for item in arr.iter_mut() {
        if let Value::Object(obj) = item {
            inline_and_strip(obj, defs, depth);
        }
    }
}

/// Resolve a `$ref` string of the form `"#/$defs/TypeName"` against `defs`.
///
/// Returns `None` for anything other than local `#/$defs/…` references.
fn resolve_ref(ref_path: &str, defs: &HashMap<String, Value>) -> Option<Value> {
    let name = ref_path
        .strip_prefix("#/$defs/")
        .or_else(|| ref_path.strip_prefix("#/definitions/"))?;
    defs.get(name).cloned()
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use rmcp::model::Tool;
    use serde_json::json;

    fn make_tool(name: &str, description: &str, schema: serde_json::Value) -> Tool {
        let schema_obj = schema.as_object().cloned().unwrap_or_default();
        let mut t = Tool::default();
        t.name = name.to_string().into();
        t.description = Some(description.to_string().into());
        t.input_schema = Arc::new(schema_obj);
        t
    }

    // ── first_sentence ────────────────────────────────────────────────────────

    #[test]
    fn first_sentence_single() {
        assert_eq!(first_sentence("Fetch a URL.", 200), "Fetch a URL");
    }

    #[test]
    fn first_sentence_multi() {
        assert_eq!(
            first_sentence("Fetch a URL. Returns raw content.", 200),
            "Fetch a URL"
        );
    }

    #[test]
    fn first_sentence_multiline() {
        assert_eq!(
            first_sentence("First line.\nSecond line.", 200),
            "First line"
        );
    }

    #[test]
    fn first_sentence_paragraph() {
        assert_eq!(
            first_sentence("\n\nSearch Jira. Supports JQL.\n\nMore info.", 200),
            "Search Jira"
        );
    }

    #[test]
    fn first_sentence_cap_at_max() {
        let long = "A".repeat(300);
        let result = first_sentence(&long, 200);
        assert_eq!(result.chars().count(), 200);
    }

    #[test]
    fn first_sentence_empty() {
        assert_eq!(first_sentence("", 200), "");
    }

    // ── Light compression ─────────────────────────────────────────────────────

    #[test]
    fn light_truncates_description() {
        let tool = make_tool(
            "search_jira",
            "Search Jira issues using JQL. Supports advanced filters.",
            json!({"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        );
        let c = SchemaCompressor::new(CompressionLevel::Light);
        let [compressed] = c.compress(vec![tool]).try_into().unwrap();
        assert_eq!(
            compressed.description.as_deref(),
            Some("Search Jira issues using JQL")
        );
    }

    #[test]
    fn light_preserves_required_and_enum() {
        let tool = make_tool(
            "post_msg",
            "Send message.",
            json!({
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "enum": ["public", "private"]},
                    "text": {"type": "string"}
                },
                "required": ["channel", "text"]
            }),
        );
        let c = SchemaCompressor::new(CompressionLevel::Light);
        let [compressed] = c.compress(vec![tool]).try_into().unwrap();
        let schema = serde_json::to_value(&*compressed.input_schema).unwrap();
        assert_eq!(
            schema["required"],
            json!(["channel", "text"]),
            "required must be preserved"
        );
        assert_eq!(
            schema["properties"]["channel"]["enum"],
            json!(["public", "private"]),
            "enum must be preserved"
        );
    }

    #[test]
    fn off_leaves_everything_unchanged() {
        let desc = "Full description. More sentences.";
        let tool = make_tool(
            "noop",
            desc,
            json!({"type": "object", "properties": {}}),
        );
        let c = SchemaCompressor::new(CompressionLevel::Off);
        let [result] = c.compress(vec![tool]).try_into().unwrap();
        assert_eq!(result.description.as_deref(), Some(desc));
    }

    // ── Aggressive compression ────────────────────────────────────────────────

    #[test]
    fn aggressive_inlines_ref() {
        let schema = json!({
            "type": "object",
            "$defs": {
                "AdfDoc": {"type": "string", "description": "ADF document"}
            },
            "properties": {
                "body": {"$ref": "#/$defs/AdfDoc"}
            },
            "required": ["body"]
        });
        let tool = make_tool("create_page", "Create a page.", schema);
        let c = SchemaCompressor::new(CompressionLevel::Aggressive);
        let [compressed] = c.compress(vec![tool]).try_into().unwrap();
        let schema = serde_json::to_value(&*compressed.input_schema).unwrap();
        assert!(schema.get("$defs").is_none(), "$defs must be removed");
        assert!(
            schema["properties"]["body"].get("$ref").is_none(),
            "$ref must be inlined"
        );
        assert_eq!(
            schema["properties"]["body"]["type"],
            json!("string"),
            "inlined type must be present"
        );
    }

    #[test]
    fn aggressive_strips_examples() {
        let schema = json!({
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "examples": ["sprint review", "Q2 planning"]
                }
            }
        });
        let tool = make_tool("search", "Search.", schema);
        let c = SchemaCompressor::new(CompressionLevel::Aggressive);
        let [compressed] = c.compress(vec![tool]).try_into().unwrap();
        let schema = serde_json::to_value(&*compressed.input_schema).unwrap();
        assert!(
            schema["properties"]["query"].get("examples").is_none(),
            "examples must be stripped"
        );
    }

    #[test]
    fn aggressive_strips_title_from_schema() {
        let schema = json!({
            "type": "object",
            "title": "CreatePageRequest",
            "properties": {
                "title": {"type": "string", "title": "Page title"}
            }
        });
        let tool = make_tool("create_page", "Create.", schema);
        let c = SchemaCompressor::new(CompressionLevel::Aggressive);
        let [compressed] = c.compress(vec![tool]).try_into().unwrap();
        let schema = serde_json::to_value(&*compressed.input_schema).unwrap();
        assert!(
            schema.get("title").is_none(),
            "top-level schema title must be removed"
        );
        assert!(
            schema["properties"]["title"].get("title").is_none(),
            "property schema title must be removed"
        );
        // The property named "title" still exists (it's a key, not a title annotation)
        assert!(
            schema["properties"].get("title").is_some(),
            "property named 'title' must still exist"
        );
    }

    #[test]
    fn aggressive_circular_ref_does_not_panic() {
        // A -> $ref B -> $ref A (circular)
        let schema = json!({
            "type": "object",
            "$defs": {
                "A": {"type": "object", "$ref": "#/$defs/B"},
                "B": {"type": "object", "$ref": "#/$defs/A"}
            },
            "properties": {
                "root": {"$ref": "#/$defs/A"}
            }
        });
        let tool = make_tool("cycle_test", "Cyclic schema.", schema);
        let c = SchemaCompressor::new(CompressionLevel::Aggressive);
        // Must not panic
        let [compressed] = c.compress(vec![tool]).try_into().unwrap();
        // $defs removed
        let schema = serde_json::to_value(&*compressed.input_schema).unwrap();
        assert!(schema.get("$defs").is_none());
    }

    #[test]
    fn aggressive_preserves_required_and_enum() {
        let schema = json!({
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["text", "image"], "examples": ["text"]},
                "content": {"type": "string"}
            },
            "required": ["type", "content"]
        });
        let tool = make_tool("post", "Post content.", schema);
        let c = SchemaCompressor::new(CompressionLevel::Aggressive);
        let [compressed] = c.compress(vec![tool]).try_into().unwrap();
        let schema = serde_json::to_value(&*compressed.input_schema).unwrap();
        assert_eq!(schema["required"], json!(["type", "content"]));
        assert_eq!(schema["properties"]["type"]["enum"], json!(["text", "image"]));
    }
}
