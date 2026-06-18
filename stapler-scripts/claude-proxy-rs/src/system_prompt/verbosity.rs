//! Verbosity steering: continuation-turn detection and suffix selection.

use serde_json::Value;

/// Returns the verbosity suffix string for the given level.
pub fn verbosity_suffix(level: u8) -> &'static str {
    match level {
        0 => "",
        1 => "Be concise.",
        2 => "Be terse. Don't restate context. Answer directly without preamble.",
        3 => "Be maximally terse. No preamble, no restatement, no ceremony. Answer only.",
        _ => "Be terse.",
    }
}

/// Returns `true` if the last human message is a continuation turn (tool results only).
///
/// A continuation turn has at least one `tool_result` block and zero `text` blocks
/// in the last `role: "user"` message content array.
pub fn is_continuation_turn(messages: &[Value]) -> bool {
    let last_user = messages
        .iter()
        .rev()
        .find(|m| m.get("role").and_then(Value::as_str) == Some("user"));

    let Some(msg) = last_user else {
        return false;
    };

    let content = match msg.get("content") {
        Some(Value::Array(arr)) => arr,
        _ => return false,
    };

    let tool_results = content
        .iter()
        .filter(|b| b.get("type").and_then(Value::as_str) == Some("tool_result"))
        .count();
    let text_blocks = content
        .iter()
        .filter(|b| b.get("type").and_then(Value::as_str) == Some("text"))
        .count();

    tool_results > 0 && text_blocks == 0
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn suffix_levels() {
        assert_eq!(verbosity_suffix(0), "");
        assert!(!verbosity_suffix(1).is_empty());
        assert!(!verbosity_suffix(2).is_empty());
        assert!(!verbosity_suffix(3).is_empty());
    }

    #[test]
    fn continuation_turn_tool_results_only() {
        let messages = vec![json!({
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]
        })];
        assert!(is_continuation_turn(&messages));
    }

    #[test]
    fn new_question_turn() {
        let messages = vec![json!({
            "role": "user",
            "content": [{"type": "text", "text": "What does this function do?"}]
        })];
        assert!(!is_continuation_turn(&messages));
    }

    #[test]
    fn mixed_content_not_continuation() {
        let messages = vec![json!({
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "x", "content": "ok"},
                {"type": "text", "text": "Also, please fix the typo."}
            ]
        })];
        assert!(!is_continuation_turn(&messages));
    }

    #[test]
    fn string_content_not_continuation() {
        let messages = vec![json!({
            "role": "user",
            "content": "plain string message longer than 20 chars yes"
        })];
        assert!(!is_continuation_turn(&messages));
    }
}
