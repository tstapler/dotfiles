//! CodeCompressor: code block compression stage.
//!
//! TODO(epic-6b): tree-sitter AST compression — strip comments, collapse
//! identical function bodies, etc.

/// Stateless code block compressor stub.
pub struct CodeCompressor;

impl CodeCompressor {
    pub fn new() -> Self {
        CodeCompressor
    }

    /// Attempt code compression for the given language.
    ///
    /// Returns `None` (pass-through) until Epic 6b implements tree-sitter
    /// AST compression.
    pub fn compress(&self, _code: &str, _language: &str) -> Option<String> {
        // TODO(epic-6b): CodeCompressor for code blocks
        None
    }
}

impl Default for CodeCompressor {
    fn default() -> Self {
        Self::new()
    }
}
