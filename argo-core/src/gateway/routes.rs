//! Request handlers for the gateway routes.

use std::sync::atomic::Ordering;
use std::sync::Arc;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::Json;
use serde_json::{json, Value};
use uuid::Uuid;

use crate::ipc;
use crate::state::AppState;

/// `GET /api/health` — liveness probe with version and uptime.
pub async fn health(State(state): State<Arc<AppState>>) -> Json<Value> {
    Json(json!({
        "status": "ok",
        "version": state.config.version,
        "uptime_s": state.started.elapsed().as_secs(),
    }))
}

/// `GET /api/version` — build/version information.
pub async fn version(State(state): State<Arc<AppState>>) -> Json<Value> {
    Json(json!({
        "version": state.config.version,
        "component": "argo-core",
    }))
}

/// `POST /api/chat` — forwards a chat request to argo-brain over IPC.
pub async fn chat(
    State(state): State<Arc<AppState>>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    state.chat_requests.fetch_add(1, Ordering::Relaxed);

    let user_id = body
        .get("user_id")
        .and_then(Value::as_str)
        .unwrap_or("anon")
        .to_string();
    let message = body
        .get("message")
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();

    // Record in the L0 cache before dispatching.
    state.memory.push(&user_id, "user", &message);

    let request = json!({
        "action": "chat",
        "id": Uuid::new_v4().to_string(),
        "user_id": user_id,
        "message": message,
        "channel": "http",
    });

    match ipc::call(&state.config.brain_socket, &request).await {
        Ok(response) => {
            if let Some(content) = response.get("content").and_then(Value::as_str) {
                state.memory.push(&user_id, "assistant", content);
            }
            Ok(Json(response))
        }
        Err(err) => {
            state.chat_errors.fetch_add(1, Ordering::Relaxed);
            tracing::warn!("chat dispatch failed: {err}");
            Err((
                StatusCode::SERVICE_UNAVAILABLE,
                Json(json!({ "error": err })),
            ))
        }
    }
}

/// `GET /api/history/:uid` — returns the L0-cached message history.
pub async fn history(
    State(state): State<Arc<AppState>>,
    Path(uid): Path<String>,
) -> Json<Value> {
    Json(json!({
        "user_id": uid,
        "history": state.memory.history(&uid),
    }))
}

/// `GET /metrics` — Prometheus text exposition (spec section 8).
pub async fn metrics(State(state): State<Arc<AppState>>) -> String {
    let requests = state.chat_requests.load(Ordering::Relaxed);
    let errors = state.chat_errors.load(Ordering::Relaxed);
    let uptime = state.started.elapsed().as_secs();

    format!(
        "# HELP argo_chat_requests_total Total chat requests\n\
         # TYPE argo_chat_requests_total counter\n\
         argo_chat_requests_total {requests}\n\
         # HELP argo_chat_errors_total Total failed chat requests\n\
         # TYPE argo_chat_errors_total counter\n\
         argo_chat_errors_total {errors}\n\
         # HELP argo_uptime_seconds Process uptime in seconds\n\
         # TYPE argo_uptime_seconds gauge\n\
         argo_uptime_seconds {uptime}\n"
    )
}
