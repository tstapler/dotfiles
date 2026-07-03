// Phase 3 — Active slot pool for dynamic tool discovery (stub)
//
// Fixed-K pool of tools registered in the active set for a Phase 3 session.
// Tools expire from the pool after slot_ttl_turns turns without being called.

use rmcp::model::Tool;

pub struct ActiveSlotPool {
    _capacity: usize,
    _ttl_turns: usize,
    _slots: Vec<Tool>,
}

impl ActiveSlotPool {
    pub fn new(capacity: usize, ttl_turns: usize) -> Self {
        Self {
            _capacity: capacity,
            _ttl_turns: ttl_turns,
            _slots: Vec::new(),
        }
    }

    pub fn add_tools(&mut self, _tools: Vec<Tool>) {
        todo!("Phase 3: add tools to active slot pool")
    }

    pub fn active_tools(&self) -> &[Tool] {
        &self._slots
    }

    pub fn on_turn_end(&mut self) {
        todo!("Phase 3: decrement TTL counters, evict expired slots")
    }
}
