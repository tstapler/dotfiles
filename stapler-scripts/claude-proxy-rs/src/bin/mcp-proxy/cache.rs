use std::sync::Arc;
use std::time::{Duration, Instant};
use rmcp::model::Tool;
use tokio::sync::RwLock;

#[derive(Debug, Clone)]
struct CachedEntry {
    tools: Vec<Tool>,
    fetched_at: Instant,
}

#[derive(Debug, Clone)]
pub struct SchemaCache {
    inner: Arc<RwLock<Option<CachedEntry>>>,
    ttl: Duration,
}

impl SchemaCache {
    pub fn new(ttl_secs: u64) -> Self {
        Self {
            inner: Arc::new(RwLock::new(None)),
            ttl: Duration::from_secs(ttl_secs),
        }
    }

    pub async fn get(&self) -> Option<Vec<Tool>> {
        let guard = self.inner.read().await;
        guard.as_ref().and_then(|entry| {
            if entry.fetched_at.elapsed() < self.ttl {
                Some(entry.tools.clone())
            } else {
                None
            }
        })
    }

    pub async fn set(&self, tools: Vec<Tool>) {
        let mut guard = self.inner.write().await;
        *guard = Some(CachedEntry { tools, fetched_at: Instant::now() });
    }

    pub async fn invalidate(&self) {
        let mut guard = self.inner.write().await;
        *guard = None;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

    fn make_tool(name: &str) -> Tool {
        let mut t = Tool::default();
        t.name = name.to_string().into();
        t
    }

    #[tokio::test]
    async fn hit_within_ttl() {
        let cache = SchemaCache::new(300);
        cache.set(vec![make_tool("tool_a")]).await;
        let result = cache.get().await;
        assert!(result.is_some());
        assert_eq!(result.unwrap()[0].name.as_ref(), "tool_a");
    }

    #[tokio::test]
    async fn miss_after_invalidate() {
        let cache = SchemaCache::new(300);
        cache.set(vec![make_tool("tool_a")]).await;
        cache.invalidate().await;
        assert!(cache.get().await.is_none());
    }
}
