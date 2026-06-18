//! Correction pattern detection from Claude Code transcript data.
//!
//! Three detection tiers, ordered by precision:
//! - Tier 1: Explicit negation / redirect phrases (high precision).
//! - Tier 2: Frustration signals (medium precision).
//! - Tier 3: Structural error-recovery loops (walk parentUuid chains).

use std::sync::LazyLock;

use regex::Regex;

use super::transcript::TranscriptEntry;

// ---------------------------------------------------------------------------
// Regex constants
// ---------------------------------------------------------------------------

/// Tier 1 — explicit negation / redirect phrases.
static TIER1: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?xi)
        \b(?:
            no[,\s]+(?:don't|do\s+not|stop|please|never)
            | don't\s+(?:do|use|add|create|make|run|call|write|put|output)
            | stop\s+(?:doing|using|adding|creating|making|that)
            | please\s+don't\s+(?:do|use|add|create|make)
            | never\s+(?:do|use|add|create|make|run|call|write|put)\s+that
            | instead[,\s]+(?:use|just|try|do|please)
            | use\s+\w+\s+instead
            | always\s+use\s+\w+
            | you\s+(?:keep|keep\s+on)\s+(?:doing|using|adding|making)
        )\b
    ",
    )
    .expect("TIER1 regex is valid")
});

/// Tier 2 — frustration / repeated correction signals.
static TIER2: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?xi)
        \b(?:
            I\s+(?:said|told|asked)\s+you\s+(?:to\s+)?(?:not|never|stop)
            | that'?s?\s+(?:wrong|not\s+right|not\s+what\s+I|incorrect)
            | why\s+(?:did|are|do)\s+you\s+(?:keep|still|always)
            | you'?re?\s+(?:still|again)\s+(?:doing|using|making)
            | how\s+many\s+times\s+(?:do\s+I\s+have\s+to|have\s+I\s+told)
            | I\s+(?:just|already)\s+said
            | (?:please\s+)?read\s+(?:the\s+)?(?:instructions|CLAUDE\.md|rules|guidelines)\s+(?:again|more\s+carefully)
            | wrong|incorrect|you're\s+doing|you\s+are\s+doing|this\s+is\s+wrong|why\s+did\s+you|you\s+should\s+have
        )\b
    ",
    )
    .expect("TIER2 regex is valid")
});

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/// A detected correction pattern mined from transcript data.
#[derive(Debug, Clone)]
pub struct CorrectionPattern {
    /// Detection tier (1 = explicit, 2 = frustration, 3 = structural loop).
    pub tier: u8,
    /// The user message that triggered this pattern.
    pub context: String,
    /// A CLAUDE.md-formatted rule suggestion.
    pub suggested_rule: String,
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Scan `entries` for correction patterns and return all matches.
///
/// Entries are expected to be in file-appearance order (as returned by
/// `transcript::parse_file`).
pub fn find_corrections(entries: &[TranscriptEntry]) -> Vec<CorrectionPattern> {
    let mut results = Vec::new();

    // Tier 1 and Tier 2 regex passes over user entries only.
    for entry in entries {
        if entry.role != "user" {
            continue;
        }
        // Skip long messages (tool outputs) — corrections are short.
        if entry.content.len() > 500 {
            continue;
        }

        if TIER1.is_match(&entry.content) {
            let rule = format!(
                "- ALWAYS/NEVER: {}",
                extract_instruction(&entry.content)
            );
            results.push(CorrectionPattern {
                tier: 1,
                context: entry.content.clone(),
                suggested_rule: rule,
            });
        } else if TIER2.is_match(&entry.content) {
            let truncated = truncate(&entry.content, 100);
            results.push(CorrectionPattern {
                tier: 2,
                context: entry.content.clone(),
                suggested_rule: format!(
                    "- Note: User indicated dissatisfaction with: {}",
                    truncated
                ),
            });
        }
    }

    // Tier 3: structural error-recovery loops.
    let tier3 = find_error_recovery_loops(entries);
    results.extend(tier3);

    results
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Extract a concise instruction from a correction message.
///
/// Returns the first sentence (up to `"."`, `"!"`, `"?"`, or 100 chars),
/// stripping leading connectors.
fn extract_instruction(text: &str) -> String {
    let sentence: &str = text
        .split_terminator(['.', '!', '?'])
        .next()
        .unwrap_or(text)
        .trim();
    truncate(sentence, 100)
}

/// Truncate `s` to at most `max` characters, appending `"…"` if cut.
fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        // Truncate at a char boundary.
        let mut end = max;
        while !s.is_char_boundary(end) {
            end -= 1;
        }
        format!("{}…", &s[..end])
    }
}

/// Tier 3: walk parentUuid chains looking for error-recovery loops.
///
/// A loop is: `assistant` turn with tool_use-style content → `user` turn that
/// appears to be a correction (Tier 1 or Tier 2 match, or content contains
/// "error") → `assistant` again. We flag the chain when it repeats ≥ 2 times
/// for entries that share a lineage.
///
/// Since we only have plain-text content here (tool_result blocks are
/// stripped), we approximate by looking for consecutive alternating
/// assistant/user pairs where the user message matches Tier 1 or Tier 2,
/// or contains the word "error"/"fail"/"wrong".
fn find_error_recovery_loops(entries: &[TranscriptEntry]) -> Vec<CorrectionPattern> {
    use std::collections::HashMap;

    // Build uuid → index map for fast parent lookup.
    let uuid_to_idx: HashMap<&str, usize> = entries
        .iter()
        .enumerate()
        .map(|(i, e)| (e.uuid.as_str(), i))
        .collect();

    let error_signal = Regex::new(r"(?i)\b(error|fail|wrong|didn't work|not working|broken)\b")
        .expect("error_signal regex is valid");

    let mut patterns = Vec::new();
    let mut flagged_uuids = std::collections::HashSet::new();

    for (i, entry) in entries.iter().enumerate() {
        if entry.role != "user" {
            continue;
        }
        if flagged_uuids.contains(entry.uuid.as_str()) {
            continue;
        }

        // Check if this user message looks like a correction signal.
        let is_correction = TIER1.is_match(&entry.content)
            || TIER2.is_match(&entry.content)
            || error_signal.is_match(&entry.content);

        if !is_correction {
            continue;
        }

        // Walk back through parentUuid chain counting alternating turns.
        let mut loop_count: u32 = 0;
        let mut current_uuid = entry.parent_uuid.as_deref();
        let mut first_correction = entry.content.clone();

        while let Some(uid) = current_uuid {
            let idx = match uuid_to_idx.get(uid) {
                Some(&idx) => idx,
                None => break,
            };
            let ancestor = &entries[idx];
            if ancestor.role == "assistant" {
                // Check the ancestor's parent for another user correction.
                if let Some(grandparent_uid) = ancestor.parent_uuid.as_deref() {
                    if let Some(&gp_idx) = uuid_to_idx.get(grandparent_uid) {
                        let gp = &entries[gp_idx];
                        if gp.role == "user"
                            && (TIER1.is_match(&gp.content)
                                || TIER2.is_match(&gp.content)
                                || error_signal.is_match(&gp.content))
                        {
                            loop_count += 1;
                            first_correction = gp.content.clone();
                            flagged_uuids.insert(gp.uuid.as_str());
                        }
                    }
                }
            }
            current_uuid = ancestor.parent_uuid.as_deref();

            if loop_count >= 2 {
                break;
            }
        }

        if loop_count >= 1 {
            // Found a repeated loop (≥ 2 correction → assistant → correction
            // cycles after combining with the current entry).
            let truncated = truncate(&first_correction, 80);
            patterns.push(CorrectionPattern {
                tier: 3,
                context: entry.content.clone(),
                suggested_rule: format!(
                    "- Pattern: Error recovery loop detected — {}",
                    truncated
                ),
            });
            flagged_uuids.insert(entry.uuid.as_str());

            // Avoid duplicate entries from nearby messages.
            // We mark the current as seen even if loop_count < 2 to keep the
            // parent walk from visiting the same chain again.
        } else if i + 2 < entries.len() {
            // Simpler structural check: look forward for assistant → same user
            // correction pattern within 4 entries (handles sequential files
            // where parentUuid chains may not be fully resolved).
            let next_assistant = entries[i + 1..].iter().take(3).find(|e| e.role == "assistant");
            let next_user = next_assistant.and_then(|_| {
                entries[i + 2..].iter().take(3).find(|e| {
                    e.role == "user"
                        && (TIER1.is_match(&e.content) || TIER2.is_match(&e.content))
                })
            });

            if let Some(next_correction) = next_user {
                let truncated = truncate(&entry.content, 80);
                patterns.push(CorrectionPattern {
                    tier: 3,
                    context: entry.content.clone(),
                    suggested_rule: format!(
                        "- Pattern: Error recovery loop detected — {}",
                        truncated
                    ),
                });
                flagged_uuids.insert(entry.uuid.as_str());
                flagged_uuids.insert(next_correction.uuid.as_str());
            }
        }
    }

    patterns
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn make_entry(uuid: &str, parent: Option<&str>, role: &str, content: &str) -> TranscriptEntry {
        TranscriptEntry {
            uuid: uuid.to_string(),
            parent_uuid: parent.map(str::to_string),
            role: role.to_string(),
            content: content.to_string(),
            is_sidechain: false,
            is_meta: false,
            session_path: PathBuf::from("/tmp/test.jsonl"),
        }
    }

    #[test]
    fn test_tier1_no_dont_match() {
        let entries = vec![make_entry("u1", None, "user", "no, don't do that again")];
        let patterns = find_corrections(&entries);
        assert!(!patterns.is_empty());
        assert_eq!(patterns[0].tier, 1);
    }

    #[test]
    fn test_tier1_stop_doing() {
        let entries = vec![make_entry("u1", None, "user", "stop doing that please")];
        let patterns = find_corrections(&entries);
        assert!(!patterns.is_empty());
        assert_eq!(patterns[0].tier, 1);
    }

    #[test]
    fn test_tier1_use_x_instead() {
        let entries = vec![make_entry("u1", None, "user", "use Edit instead")];
        let patterns = find_corrections(&entries);
        assert!(!patterns.is_empty());
        assert_eq!(patterns[0].tier, 1);
    }

    #[test]
    fn test_tier2_wrong_match() {
        let entries = vec![make_entry("u1", None, "user", "that's wrong, try again")];
        let patterns = find_corrections(&entries);
        assert!(!patterns.is_empty());
        assert_eq!(patterns[0].tier, 2);
    }

    #[test]
    fn test_tier2_frustration_how_many_times() {
        let entries = vec![make_entry(
            "u1",
            None,
            "user",
            "how many times have I told you to not use cat",
        )];
        let patterns = find_corrections(&entries);
        assert!(!patterns.is_empty());
        assert_eq!(patterns[0].tier, 2);
    }

    #[test]
    fn test_assistant_entries_ignored() {
        let entries = vec![make_entry(
            "a1",
            None,
            "assistant",
            "no, don't do that — I'm the assistant",
        )];
        let patterns = find_corrections(&entries);
        // Correction regexes only apply to user entries.
        assert!(patterns.is_empty());
    }

    #[test]
    fn test_tier1_suggested_rule_format() {
        let entries = vec![make_entry(
            "u1",
            None,
            "user",
            "don't use cat, use Read instead",
        )];
        let patterns = find_corrections(&entries);
        assert!(patterns[0].suggested_rule.starts_with("- ALWAYS/NEVER:"));
    }

    #[test]
    fn test_tier2_suggested_rule_format() {
        let entries = vec![make_entry("u1", None, "user", "wrong, do it differently")];
        let patterns = find_corrections(&entries);
        assert!(patterns[0].suggested_rule.starts_with("- Note: User indicated dissatisfaction with:"));
    }

    #[test]
    fn test_truncate() {
        let s = "a".repeat(200);
        let t = truncate(&s, 100);
        assert!(t.len() <= 104); // 100 bytes + "…" (3 bytes)
    }

    #[test]
    fn test_no_false_positives_on_normal_message() {
        let entries = vec![make_entry(
            "u1",
            None,
            "user",
            "please summarize this document",
        )];
        let patterns = find_corrections(&entries);
        assert!(patterns.is_empty());
    }
}
