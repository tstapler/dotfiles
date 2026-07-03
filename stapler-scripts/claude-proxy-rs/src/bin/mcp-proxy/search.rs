// Phase 3 — BM25 dynamic tool discovery (stub)
//
// This module will implement BM25 + fastembed hybrid search over the full
// RawCatalog. Active in Phase 3 only (phase3.enabled = true in mcp-proxy.toml).

use rmcp::model::Tool;

pub struct BM25Index {
    _tools: Vec<Tool>,
}

impl BM25Index {
    pub fn build(_tools: Vec<Tool>) -> Self {
        todo!("Phase 3: BM25 index construction")
    }

    pub fn search(&self, _query: &str, _top_k: usize) -> Vec<Tool> {
        todo!("Phase 3: BM25 search")
    }
}
