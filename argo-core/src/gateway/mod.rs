//! HTTP gateway — spec section 4.1.
//!
//! Builds the Axum router. The route set is the skeleton subset; WebSocket,
//! SSE streaming and the OpenAI-compatible endpoints arrive in later sprints.

mod routes;

use std::sync::Arc;

use axum::routing::{get, post};
use axum::Router;

use crate::state::AppState;

/// Constructs the gateway router with shared application state.
pub fn router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/api/health", get(routes::health))
        .route("/api/version", get(routes::version))
        .route("/api/chat", post(routes::chat))
        .route("/api/history/:uid", get(routes::history))
        // WebSocket chat endpoint.
        .route("/ws/:uid", get(routes::ws))
        // OpenAI-compatible chat completions endpoint.
        .route("/v1/chat/completions", post(routes::chat_completions))
        .route("/metrics", get(routes::metrics))
        .with_state(state)
}
