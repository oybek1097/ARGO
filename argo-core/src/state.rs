//! Shared application state passed to every request handler.

use std::sync::atomic::AtomicU64;
use std::time::Instant;

use crate::config::Config;
use crate::memory::WorkingMemory;

/// State shared across all gateway handlers (wrapped in an `Arc`).
pub struct AppState {
    pub config: Config,
    pub memory: WorkingMemory,
    pub started: Instant,
    /// Counter: total chat requests received.
    pub chat_requests: AtomicU64,
    /// Counter: chat requests that failed (e.g. brain unreachable).
    pub chat_errors: AtomicU64,
}

impl AppState {
    pub fn new(config: Config) -> Self {
        Self {
            config,
            memory: WorkingMemory::new(),
            started: Instant::now(),
            chat_requests: AtomicU64::new(0),
            chat_errors: AtomicU64::new(0),
        }
    }
}
