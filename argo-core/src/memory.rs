//! L0 working memory — spec section 4.3.
//!
//! The fastest memory layer: a per-user ring buffer kept entirely in process
//! memory. Durable layers (L1 SQLite, L2 vector) live in argo-brain.

use std::collections::VecDeque;

use dashmap::DashMap;
use serde::Serialize;

/// Maximum number of messages retained per user.
const MAX_PER_USER: usize = 200;

/// A single cached message.
#[derive(Clone, Serialize)]
pub struct Entry {
    pub role: String,
    pub content: String,
}

/// Concurrent, per-user ring buffer of recent messages.
#[derive(Default)]
pub struct WorkingMemory {
    store: DashMap<String, VecDeque<Entry>>,
}

impl WorkingMemory {
    pub fn new() -> Self {
        Self::default()
    }

    /// Appends a message, evicting the oldest entry past the cap.
    pub fn push(&self, user: &str, role: &str, content: &str) {
        let mut queue = self.store.entry(user.to_string()).or_default();
        if queue.len() >= MAX_PER_USER {
            queue.pop_front();
        }
        queue.push_back(Entry {
            role: role.to_string(),
            content: content.to_string(),
        });
    }

    /// Returns a snapshot of the user's cached history (oldest first).
    pub fn history(&self, user: &str) -> Vec<Entry> {
        self.store
            .get(user)
            .map(|queue| queue.iter().cloned().collect())
            .unwrap_or_default()
    }
}
