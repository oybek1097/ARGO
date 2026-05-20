//! Request handlers for the gateway routes.

use std::convert::Infallible;
use std::net::SocketAddr;
use std::sync::atomic::Ordering;
use std::sync::Arc;

use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{ConnectInfo, Path, State};
use axum::http::StatusCode;
use axum::response::sse::{Event, KeepAlive, Sse};
use axum::response::Response;
use axum::Json;
use futures::stream::{self, Stream};
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
///
/// Guarded by the per-IP rate limiter: clients exceeding the configured
/// budget receive HTTP 429 before any work is dispatched to the brain.
pub async fn chat(
    State(state): State<Arc<AppState>>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let client_ip = peer.ip().to_string();
    if !state.rate_limiter.check(&client_ip) {
        tracing::warn!("rate limit exceeded for {client_ip}");
        return Err((
            StatusCode::TOO_MANY_REQUESTS,
            Json(json!({ "error": "rate limit exceeded" })),
        ));
    }

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

/// `POST /api/chat/stream` — Server-Sent Events streaming chat endpoint.
///
/// Forwards the chat request to argo-brain over IPC, then streams the result
/// back to the client as SSE `data:` frames followed by a terminal
/// `data: [DONE]` frame.
///
/// Note: argo-brain currently returns a single complete response per call, so
/// this skeleton emits the whole reply as one `data:` frame. The framing is
/// already token-stream-shaped, so a future incremental brain protocol can
/// drop in without changing the wire contract.
pub async fn chat_stream(
    State(state): State<Arc<AppState>>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    Json(body): Json<Value>,
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let client_ip = peer.ip().to_string();

    // The rate limiter guards the streaming endpoint too; an over-limit
    // client gets an error frame rather than an HTTP status (the SSE
    // response has already begun by the time the body streams).
    if !state.rate_limiter.check(&client_ip) {
        tracing::warn!("rate limit exceeded for {client_ip} (stream)");
        let events = vec![
            Ok(Event::default().data(json!({ "error": "rate limit exceeded" }).to_string())),
            Ok(Event::default().data("[DONE]")),
        ];
        return Sse::new(stream::iter(events)).keep_alive(KeepAlive::default());
    }

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

    state.memory.push(&user_id, "user", &message);

    let request = json!({
        "action": "chat",
        "id": Uuid::new_v4().to_string(),
        "user_id": user_id,
        "message": message,
        "channel": "http-sse",
    });

    let mut events: Vec<Result<Event, Infallible>> = Vec::new();
    match ipc::call(&state.config.brain_socket, &request).await {
        Ok(response) => {
            if let Some(content) = response.get("content").and_then(Value::as_str) {
                state.memory.push(&user_id, "assistant", content);
            }
            events.push(Ok(Event::default().data(response.to_string())));
        }
        Err(err) => {
            state.chat_errors.fetch_add(1, Ordering::Relaxed);
            tracing::warn!("sse chat dispatch failed: {err}");
            events.push(Ok(
                Event::default().data(json!({ "error": err }).to_string())
            ));
        }
    }
    // Terminal frame: signals the client the stream is complete.
    events.push(Ok(Event::default().data("[DONE]")));

    Sse::new(stream::iter(events)).keep_alive(KeepAlive::default())
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

/// Length of the stub embedding vector.
const STUB_EMBEDDING_DIM: usize = 16;

/// Produces a deterministic pseudo-embedding for `input`.
///
/// STUB IMPLEMENTATION — argo-core ships no embedding model. This derives a
/// fixed-length float vector purely by hashing the input string, so the same
/// input always yields the same vector. The values carry no semantic meaning
/// and must NOT be used for real similarity search; they exist only so the
/// `/v1/embeddings` endpoint has a stable, OpenAI-shaped contract until a real
/// embedding model is wired into argo-brain.
fn stub_embedding(input: &str) -> Vec<f32> {
    // FNV-1a 64-bit hash, seeded per dimension index for variation.
    (0..STUB_EMBEDDING_DIM)
        .map(|i| {
            let mut hash: u64 = 0xcbf29ce484222325 ^ (i as u64).wrapping_mul(0x100000001b3);
            for byte in input.bytes() {
                hash ^= byte as u64;
                hash = hash.wrapping_mul(0x100000001b3);
            }
            // Map the hash into a deterministic float in [-1.0, 1.0).
            let unit = (hash as f64) / (u64::MAX as f64);
            (unit * 2.0 - 1.0) as f32
        })
        .collect()
}

/// `POST /v1/embeddings` — OpenAI-compatible embeddings endpoint.
///
/// Accepts `{"model": ..., "input": ...}` where `input` is a string (or a
/// JSON array of strings). Returns an OpenAI-shaped `list` of embedding
/// objects.
///
/// STUB: the embeddings are deterministic hashes of the input, not real
/// semantic vectors — see [`stub_embedding`].
pub async fn embeddings(Json(body): Json<Value>) -> Json<Value> {
    let model = body
        .get("model")
        .and_then(Value::as_str)
        .unwrap_or("argo-embed-stub")
        .to_string();

    // `input` may be a single string or an array of strings.
    let inputs: Vec<String> = match body.get("input") {
        Some(Value::String(s)) => vec![s.clone()],
        Some(Value::Array(arr)) => arr
            .iter()
            .map(|v| v.as_str().unwrap_or("").to_string())
            .collect(),
        _ => vec![String::new()],
    };

    let data: Vec<Value> = inputs
        .iter()
        .enumerate()
        .map(|(index, text)| {
            json!({
                "object": "embedding",
                "index": index,
                "embedding": stub_embedding(text),
            })
        })
        .collect();

    Json(json!({
        "object": "list",
        "data": data,
        "model": model,
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
