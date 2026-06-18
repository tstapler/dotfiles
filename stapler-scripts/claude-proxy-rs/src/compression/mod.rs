//! Compression pipeline.
//!
//! Provides a native text compression engine that ports the observable
//! behaviors of the Python `compactor.py` / FusionEngine at the
//! `/v1/messages` boundary: floor check, double-compression guard,
//! tool-pair orphan guard, Rewind marker injection, and Rewind tool injection.

pub mod code_compressor;
pub mod engine;
pub mod rewind;
pub mod smart_crusher;
pub mod text_compressor;

// Re-exports for convenient use from other modules.
pub use code_compressor::CodeCompressor;
pub use engine::{CompressionConfig, CompressionEngine, CompressionStats};
pub use rewind::RewindStore;
pub use smart_crusher::SmartCrusher;
pub use text_compressor::TextCompressor;

/// Retrieve original (pre-compression) content from the RewindStore by hash ID.
///
/// Returns the content as a UTF-8 `String`, or `None` if the hash is not found
/// or the stored bytes are not valid UTF-8.
pub async fn rewind_retrieve_handler(hash_id: &str, store: &RewindStore) -> Option<String> {
    let arc_bytes = store.retrieve(hash_id).await?;
    std::str::from_utf8(&arc_bytes).ok().map(|s| s.to_string())
}
