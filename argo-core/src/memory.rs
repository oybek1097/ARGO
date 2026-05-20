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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn push_then_history_returns_entries_in_order() {
        let mem = WorkingMemory::new();
        mem.push("alice", "user", "hello");
        mem.push("alice", "assistant", "hi there");
        mem.push("alice", "user", "how are you");

        let history = mem.history("alice");
        assert_eq!(history.len(), 3);
        assert_eq!(history[0].role, "user");
        assert_eq!(history[0].content, "hello");
        assert_eq!(history[1].role, "assistant");
        assert_eq!(history[1].content, "hi there");
        assert_eq!(history[2].content, "how are you");
    }

    #[test]
    fn history_for_unknown_user_is_empty() {
        let mem = WorkingMemory::new();
        assert!(mem.history("nobody").is_empty());
    }

    #[test]
    fn ring_buffer_caps_at_max_per_user() {
        let mem = WorkingMemory::new();
        // Push more than the cap; oldest entries must be evicted.
        for i in 0..(MAX_PER_USER + 50) {
            mem.push("bob", "user", &format!("msg-{i}"));
        }

        let history = mem.history("bob");
        assert_eq!(history.len(), MAX_PER_USER);
        // The first 50 messages should have been evicted (msg-0..msg-49).
        assert_eq!(history.first().unwrap().content, "msg-50");
        assert_eq!(
            history.last().unwrap().content,
            format!("msg-{}", MAX_PER_USER + 49)
        );
    }

    #[test]
    fn users_are_isolated_from_each_other() {
        let mem = WorkingMemory::new();
        mem.push("u1", "user", "one");
        mem.push("u2", "user", "two");
        mem.push("u2", "user", "two-again");

        let h1 = mem.history("u1");
        let h2 = mem.history("u2");
        assert_eq!(h1.len(), 1);
        assert_eq!(h1[0].content, "one");
        assert_eq!(h2.len(), 2);
        assert_eq!(h2[0].content, "two");
        assert_eq!(h2[1].content, "two-again");
    }
}
