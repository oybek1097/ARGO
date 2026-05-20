//! Request handlers for the gateway routes.

use std::sync::atomic::Ordering;
use std::sync::Arc;

use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::Response;
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

/// `GET /ws/:uid` — upgrades the connection to a WebSocket.
///
/// Each inbound text message is treated as a chat message from `uid`,
/// forwarded to argo-brain over IPC, and the brain's response content is
/// sent back over the socket as a text message.
pub async fn ws(
    State(state): State<Arc<AppState>>,
    Path(uid): Path<String>,
    upgrade: WebSocketUpgrade,
) -> Response {
    upgrade.on_upgrade(move |socket| handle_ws(socket, state, uid))
}

/// Drives a single WebSocket session until the peer disconnects.
async fn handle_ws(mut socket: WebSocket, state: Arc<AppState>, uid: String) {
    while let Some(Ok(msg)) = socket.recv().await {
        // Only text frames carry chat messages; ignore everything else.
        let text = match msg {
            Message::Text(text) => text,
            Message::Close(_) => break,
            _ => continue,
        };

        state.chat_requests.fetch_add(1, Ordering::Relaxed);

        // Record the inbound message in the L0 cache before dispatching.
        state.memory.push(&uid, "user", &text);

        let request = json!({
            "action": "chat",
            "id": Uuid::new_v4().to_string(),
            "user_id": uid,
            "message": text,
            "channel": "ws",
        });

        // Forward to argo-brain and reply with the response content.
        let reply = match ipc::call(&state.config.brain_socket, &request).await {
            Ok(response) => {
                let content = response
                    .get("content")
                    .and_then(Value::as_str)
                    .unwrap_or("")
                    .to_string();
                state.memory.push(&uid, "assistant", &content);
                content
            }
            Err(err) => {
                state.chat_errors.fetch_add(1, Ordering::Relaxed);
                tracing::warn!("ws chat dispatch failed: {err}");
                json!({ "error": err }).to_string()
            }
        };

        // If the send fails the peer is gone; stop the session.
        if socket.send(Message::Text(reply)).await.is_err() {
            break;
        }
    }
}

/// `POST /v1/chat/completions` — OpenAI-compatible chat completion endpoint.
///
/// Accepts an OpenAI-style request body, takes the last user message,
/// forwards it to argo-brain over IPC, and returns an OpenAI-shaped
/// `chat.completion` JSON response.
pub async fn chat_completions(
    State(state): State<Arc<AppState>>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    state.chat_requests.fetch_add(1, Ordering::Relaxed);

    let model = body
        .get("model")
        .and_then(Value::as_str)
        .unwrap_or("argo")
        .to_string();

    // Pick the content of the last message whose role is "user".
    let message = body
        .get("messages")
        .and_then(Value::as_array)
        .and_then(|messages| {
            messages
                .iter()
                .rev()
                .find(|m| m.get("role").and_then(Value::as_str) == Some("user"))
        })
        .and_then(|m| m.get("content").and_then(Value::as_str))
        .unwrap_or("")
        .to_string();

    let user_id = "openai";

    // Record in the L0 cache before dispatching.
    state.memory.push(user_id, "user", &message);

    let request = json!({
        "action": "chat",
        "id": Uuid::new_v4().to_string(),
        "user_id": user_id,
        "message": message,
        "channel": "openai",
    });

    match ipc::call(&state.config.brain_socket, &request).await {
        Ok(response) => {
            let content = response
                .get("content")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_string();
            state.memory.push(user_id, "assistant", &content);

            Ok(Json(json!({
                "id": format!("chatcmpl-{}", Uuid::new_v4()),
                "object": "chat.completion",
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }],
            })))
        }
        Err(err) => {
            state.chat_errors.fetch_add(1, Ordering::Relaxed);
            tracing::warn!("openai chat dispatch failed: {err}");
            Err((
                StatusCode::SERVICE_UNAVAILABLE,
                Json(json!({ "error": err })),
            ))
        }
    }
}

/// `GET /v1/models` — OpenAI-compatible model listing.
///
/// Returns the static set of model ids this gateway accepts. The ids are
/// interchangeable; every request is ultimately dispatched to argo-brain.
pub async fn models() -> Json<Value> {
    Json(json!({
        "object": "list",
        "data": [
            { "id": "argo", "object": "model", "owned_by": "argo" },
            { "id": "argo-brain", "object": "model", "owned_by": "argo" },
        ],
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
