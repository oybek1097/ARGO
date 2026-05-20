//! argo-core — the Rust gateway of ARGO Agent v3.0.
//!
//! This is the small, hardened external face described in spec section 4.1.
//! It terminates HTTP, keeps an L0 working-memory cache and forwards agent
//! work to `argo-brain` over a Unix-socket IPC channel.
//!
//! The skeleton ships the core endpoints (`/api/health`, `/api/version`,
//! `/api/chat`, `/api/history/:uid`, `/metrics`). WebSocket, the OpenAI-
//! compatible surface and the security sandbox arrive in later sprints.

mod config;
mod gateway;
mod ipc;
mod memory;
mod state;

use std::sync::Arc;

use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    let config = config::Config::from_env();
    let state = Arc::new(state::AppState::new(config.clone()));
    let app = gateway::router(state.clone());

    let listener = tokio::net::TcpListener::bind((config.host.as_str(), config.port))
        .await
        .expect("failed to bind the listen address");

    tracing::info!(
        "argo-core v{} listening on http://{}:{} (brain socket: {})",
        config.version,
        config.host,
        config.port,
        config.brain_socket,
    );

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .expect("server error");

    tracing::info!("argo-core stopped");
}

/// Resolves when the process receives Ctrl-C, triggering graceful shutdown.
async fn shutdown_signal() {
    let _ = tokio::signal::ctrl_c().await;
    tracing::info!("shutdown signal received");
}
