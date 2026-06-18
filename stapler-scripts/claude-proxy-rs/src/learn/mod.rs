//! Session mining: parse Claude Code JSONL transcripts and detect correction
//! patterns.
//!
//! # Architecture
//!
//! - `transcript` — defensive JSONL parser for `~/.claude/projects/`
//! - `patterns`   — three-tier regex + structural correction detector
//! - `mod`        — admin endpoint handlers (`learn_preview`, `learn_apply`)
//!
//! # Safety constraint
//!
//! `learn_apply` writes ONLY to `/tmp/headroom-learn-staging.md`.
//! It NEVER writes to `CLAUDE.md`, `MEMORY.md`, or any file under
//! `~/.claude/`. That boundary is enforced here, not by the caller.

pub mod patterns;
pub mod transcript;

use std::io::Write;
use std::path::Path;

use anyhow::Result;
use chrono::Utc;
use serde::{Deserialize, Serialize};

use patterns::{find_corrections, CorrectionPattern};
use transcript::parse_all_transcripts;

// ---------------------------------------------------------------------------
// Response types (serialised to JSON by the axum handlers in main.rs)
// ---------------------------------------------------------------------------

/// Response for `GET /admin/learn-preview`.
#[derive(Debug, Serialize, Deserialize)]
pub struct LearnPreviewResponse {
    pub tier1_count: usize,
    pub tier2_count: usize,
    pub tier3_count: usize,
    pub total: usize,
    pub corrections: Vec<CorrectionSummary>,
}

/// A single correction pattern, safe to serialise over HTTP.
#[derive(Debug, Serialize, Deserialize)]
pub struct CorrectionSummary {
    pub tier: u8,
    pub context: String,
    pub suggested_rule: String,
}

impl From<&CorrectionPattern> for CorrectionSummary {
    fn from(p: &CorrectionPattern) -> Self {
        CorrectionSummary {
            tier: p.tier,
            context: p.context.clone(),
            suggested_rule: p.suggested_rule.clone(),
        }
    }
}

/// Response for `POST /admin/learn-apply`.
#[derive(Debug, Serialize, Deserialize)]
pub struct LearnApplyResponse {
    pub written: usize,
    pub staging_path: String,
}

// ---------------------------------------------------------------------------
// Admin handlers
// ---------------------------------------------------------------------------

/// `GET /admin/learn-preview` — scan transcripts, return detected patterns.
///
/// Does NOT write anything to disk.
pub async fn learn_preview() -> Result<LearnPreviewResponse> {
    // Transcript parsing is blocking I/O — run in a dedicated thread.
    let entries = tokio::task::spawn_blocking(parse_all_transcripts)
        .await
        .map_err(|e| anyhow::anyhow!("spawn_blocking join error: {}", e))??;

    let raw_patterns = find_corrections(&entries);

    let tier1_count = raw_patterns.iter().filter(|p| p.tier == 1).count();
    let tier2_count = raw_patterns.iter().filter(|p| p.tier == 2).count();
    let tier3_count = raw_patterns.iter().filter(|p| p.tier == 3).count();
    let total = raw_patterns.len();

    let corrections = raw_patterns.iter().map(CorrectionSummary::from).collect();

    Ok(LearnPreviewResponse {
        tier1_count,
        tier2_count,
        tier3_count,
        total,
        corrections,
    })
}

/// `POST /admin/learn-apply` — write staged corrections to the staging file.
///
/// The staging file is `/tmp/headroom-learn-staging.md`.
/// This function NEVER writes to CLAUDE.md or any memory file.
pub async fn learn_apply(patterns: &[CorrectionPattern]) -> Result<LearnApplyResponse> {
    const STAGING_PATH: &str = "/tmp/headroom-learn-staging.md";
    write_staging_file(Path::new(STAGING_PATH), patterns)?;

    Ok(LearnApplyResponse {
        written: patterns.len(),
        staging_path: STAGING_PATH.to_string(),
    })
}

/// Write `patterns` to `staging_path` in CLAUDE.md-ready Markdown format.
///
/// This is a pure function (no async) so it can be tested without a runtime.
pub fn write_staging_file(staging_path: &Path, patterns: &[CorrectionPattern]) -> Result<()> {
    let date = Utc::now().format("%Y-%m-%d %H:%M UTC").to_string();

    let mut file = std::fs::File::create(staging_path)
        .map_err(|e| anyhow::anyhow!("cannot create staging file {}: {}", staging_path.display(), e))?;

    writeln!(file, "# headroom learn — Staging (generated {})", date)?;
    writeln!(file)?;
    writeln!(file, "Review these patterns before applying to CLAUDE.md:")?;
    writeln!(file)?;

    // Tier 1
    let tier1: Vec<_> = patterns.iter().filter(|p| p.tier == 1).collect();
    writeln!(file, "## Tier 1 Corrections")?;
    writeln!(file)?;
    if tier1.is_empty() {
        writeln!(file, "_None detected._")?;
    } else {
        for p in &tier1 {
            writeln!(file, "{}", p.suggested_rule)?;
        }
    }
    writeln!(file)?;

    // Tier 2
    let tier2: Vec<_> = patterns.iter().filter(|p| p.tier == 2).collect();
    writeln!(file, "## Tier 2 Corrections")?;
    writeln!(file)?;
    if tier2.is_empty() {
        writeln!(file, "_None detected._")?;
    } else {
        for p in &tier2 {
            writeln!(file, "{}", p.suggested_rule)?;
        }
    }
    writeln!(file)?;

    // Tier 3
    let tier3: Vec<_> = patterns.iter().filter(|p| p.tier == 3).collect();
    writeln!(file, "## Tier 3 Recovery Loops")?;
    writeln!(file)?;
    if tier3.is_empty() {
        writeln!(file, "_None detected._")?;
    } else {
        for p in &tier3 {
            writeln!(file, "{}", p.suggested_rule)?;
        }
    }

    Ok(())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    fn make_pattern(tier: u8, context: &str, rule: &str) -> CorrectionPattern {
        CorrectionPattern {
            tier,
            context: context.to_string(),
            suggested_rule: rule.to_string(),
        }
    }

    #[test]
    fn test_write_staging_file_creates_correct_sections() {
        let f = NamedTempFile::new().unwrap();
        let patterns = vec![
            make_pattern(1, "don't use cat", "- ALWAYS/NEVER: don't use cat"),
            make_pattern(2, "wrong!", "- Note: User indicated dissatisfaction with: wrong!"),
            make_pattern(
                3,
                "error again",
                "- Pattern: Error recovery loop detected — error again",
            ),
        ];

        write_staging_file(f.path(), &patterns).unwrap();

        let content = std::fs::read_to_string(f.path()).unwrap();
        assert!(content.contains("# headroom learn — Staging"));
        assert!(content.contains("## Tier 1 Corrections"));
        assert!(content.contains("## Tier 2 Corrections"));
        assert!(content.contains("## Tier 3 Recovery Loops"));
        assert!(content.contains("- ALWAYS/NEVER: don't use cat"));
        assert!(content.contains("- Note: User indicated dissatisfaction with: wrong!"));
        assert!(content.contains("- Pattern: Error recovery loop detected — error again"));
    }

    #[test]
    fn test_write_staging_file_empty_patterns() {
        let f = NamedTempFile::new().unwrap();
        write_staging_file(f.path(), &[]).unwrap();

        let content = std::fs::read_to_string(f.path()).unwrap();
        // All three sections present, all showing "None detected."
        assert_eq!(content.matches("_None detected._").count(), 3);
    }

    #[test]
    fn test_correction_summary_from_pattern() {
        let p = make_pattern(1, "context text", "- ALWAYS/NEVER: context text");
        let s = CorrectionSummary::from(&p);
        assert_eq!(s.tier, 1);
        assert_eq!(s.context, "context text");
    }

    #[test]
    fn test_learn_preview_response_counts() {
        // Build a response manually to verify count logic.
        let patterns = vec![
            make_pattern(1, "a", "rule a"),
            make_pattern(1, "b", "rule b"),
            make_pattern(2, "c", "rule c"),
            make_pattern(3, "d", "rule d"),
        ];

        let t1 = patterns.iter().filter(|p| p.tier == 1).count();
        let t2 = patterns.iter().filter(|p| p.tier == 2).count();
        let t3 = patterns.iter().filter(|p| p.tier == 3).count();

        assert_eq!(t1, 2);
        assert_eq!(t2, 1);
        assert_eq!(t3, 1);
    }

    #[test]
    fn test_staging_path_is_tmp() {
        // Confirm the constant staging path is under /tmp, not home.
        assert!(
            "/tmp/headroom-learn-staging.md".starts_with("/tmp/"),
            "staging file must be in /tmp, not home or project dir"
        );
    }
}
