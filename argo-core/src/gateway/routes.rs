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

/// Builds a JSON-RPC 2.0 error object response.
///
/// `id` is echoed back from the request (JSON null if absent). `code` and
/// `message` follow the JSON-RPC 2.0 spec error conventions.
fn jsonrpc_error(id: Value, code: i64, message: &str) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "error": { "code": code, "message": message },
    })
}

/// Builds a JSON-RPC 2.0 success response.
fn jsonrpc_result(id: Value, result: Value) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": result,
    })
}

/// Dispatches a single MCP JSON-RPC 2.0 request to its handler.
///
/// This is the pure, testable core of the `/mcp` endpoint: given a parsed
/// JSON-RPC request `Value`, it returns the JSON-RPC response `Value`. It has
/// no I/O and no dependency on application state, so it can be unit-tested
/// directly.
///
/// Supported methods:
/// - `initialize` — handshake; returns protocol version, capabilities, server info.
/// - `tools/list` — argo-core owns no tools, so this returns an empty list.
/// - `ping` — liveness check; returns an empty result object.
///
/// Any other method yields a JSON-RPC `-32601` (method not found) error.
/// A request missing the `method` field yields `-32600` (invalid request).
pub fn dispatch_mcp(request: &Value) -> Value {
    // The id is echoed verbatim; absent ids become JSON null per the spec.
    let id = request.get("id").cloned().unwrap_or(Value::Null);

    let method = match request.get("method").and_then(Value::as_str) {
        Some(method) => method,
        None => return jsonrpc_error(id, -32600, "Invalid Request: missing method"),
    };

    match method {
        "initialize" => jsonrpc_result(
            id,
            json!({
                "protocolVersion": "2024-11-05",
                "capabilities": { "tools": {} },
                "serverInfo": { "name": "argo-core", "version": env!("CARGO_PKG_VERSION") },
            }),
        ),
        "tools/list" => jsonrpc_result(id, json!({ "tools": [] })),
        "ping" => jsonrpc_result(id, json!({})),
        other => jsonrpc_error(id, -32601, &format!("Method not found: {other}")),
    }
}

/// `POST /mcp` — minimal Model Context Protocol JSON-RPC 2.0 endpoint.
///
/// Accepts a JSON-RPC 2.0 request and dispatches it via [`dispatch_mcp`].
/// argo-core itself owns no tools; this endpoint exists so MCP clients can
/// complete the `initialize` handshake and discover the (empty) tool set.
pub async fn mcp(Json(body): Json<Value>) -> Json<Value> {
    Json(dispatch_mcp(&body))
}

/// Extracts the prompt text from a Responses-API `input` field.
///
/// The OpenAI Responses API allows `input` to be either a bare string or an
/// array of message objects. This helper normalises both into a single string:
/// for the array form it concatenates the text of every `input_text` content
/// part across all messages. Anything unrecognised yields an empty string.
pub fn extract_responses_input(input: &Value) -> String {
    match input {
        Value::String(s) => s.clone(),
        Value::Array(messages) => {
            let mut parts: Vec<String> = Vec::new();
            for message in messages {
                match message.get("content") {
                    // content may itself be a plain string.
                    Some(Value::String(s)) => parts.push(s.clone()),
                    // ...or an array of typed content parts.
                    Some(Value::Array(content)) => {
                        for part in content {
                            if let Some(text) = part.get("text").and_then(Value::as_str) {
                                parts.push(text.to_string());
                            }
                        }
                    }
                    _ => {}
                }
            }
            parts.join("\n")
        }
        _ => String::new(),
    }
}

/// `POST /v1/responses` — OpenAI Responses API endpoint.
///
/// Accepts `{"model": ..., "input": ...}` where `input` is a string (or an
/// array of Responses-API message objects). Forwards the extracted input text
/// to argo-brain over IPC and returns an OpenAI Responses-shaped JSON object.
pub async fn responses(
    State(state): State<Arc<AppState>>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    state.chat_requests.fetch_add(1, Ordering::Relaxed);

    let model = body
        .get("model")
        .and_then(Value::as_str)
        .unwrap_or("argo")
        .to_string();

    let message = body
        .get("input")
        .map(extract_responses_input)
        .unwrap_or_default();

    let user_id = "openai-responses";
    state.memory.push(user_id, "user", &message);

    let request = json!({
        "action": "chat",
        "id": Uuid::new_v4().to_string(),
        "user_id": user_id,
        "message": message,
        "channel": "openai-responses",
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
                "id": format!("resp-{}", Uuid::new_v4()),
                "object": "response",
                "model": model,
                "output": [{
                    "type": "message",
                    "role": "assistant",
                    "content": [{
                        "type": "output_text",
                        "text": content,
                    }],
                }],
                "status": "completed",
            })))
        }
        Err(err) => {
            state.chat_errors.fetch_add(1, Ordering::Relaxed);
            tracing::warn!("responses dispatch failed: {err}");
            Err((
                StatusCode::SERVICE_UNAVAILABLE,
                Json(json!({ "error": err })),
            ))
        }
    }
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

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn dispatch_mcp_initialize_returns_protocol_version() {
        let request = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
        });
        let response = dispatch_mcp(&request);

        assert_eq!(response["jsonrpc"], "2.0");
        assert_eq!(response["id"], 1);
        assert_eq!(response["result"]["protocolVersion"], "2024-11-05");
        assert_eq!(response["result"]["serverInfo"]["name"], "argo-core");
        // capabilities must be present so clients can negotiate.
        assert!(response["result"]["capabilities"].is_object());
        // No error branch on a known method.
        assert!(response.get("error").is_none());
    }

    #[test]
    fn dispatch_mcp_tools_list_returns_empty_list() {
        let request = json!({
            "jsonrpc": "2.0",
            "id": "abc",
            "method": "tools/list",
        });
        let response = dispatch_mcp(&request);

        assert_eq!(response["id"], "abc");
        let tools = response["result"]["tools"]
            .as_array()
            .expect("tools must be an array");
        assert!(tools.is_empty());
    }

    #[test]
    fn dispatch_mcp_ping_returns_empty_result() {
        let request = json!({ "jsonrpc": "2.0", "id": 7, "method": "ping" });
        let response = dispatch_mcp(&request);

        assert_eq!(response["id"], 7);
        assert!(response["result"].is_object());
        assert!(response.get("error").is_none());
    }

    #[test]
    fn dispatch_mcp_unknown_method_returns_method_not_found() {
        let request = json!({
            "jsonrpc": "2.0",
            "id": 42,
            "method": "does/not/exist",
        });
        let response = dispatch_mcp(&request);

        assert_eq!(response["id"], 42);
        assert_eq!(response["error"]["code"], -32601);
        assert!(response.get("result").is_none());
    }

    #[test]
    fn dispatch_mcp_missing_method_returns_invalid_request() {
        let request = json!({ "jsonrpc": "2.0", "id": 9 });
        let response = dispatch_mcp(&request);

        assert_eq!(response["id"], 9);
        assert_eq!(response["error"]["code"], -32600);
    }

    #[test]
    fn dispatch_mcp_missing_id_echoes_null() {
        let request = json!({ "jsonrpc": "2.0", "method": "ping" });
        let response = dispatch_mcp(&request);

        // Absent ids must be echoed back as JSON null.
        assert!(response["id"].is_null());
    }

    #[test]
    fn extract_responses_input_handles_plain_string() {
        let input = json!("hello world");
        assert_eq!(extract_responses_input(&input), "hello world");
    }

    #[test]
    fn extract_responses_input_handles_message_array() {
        let input = json!([
            {
                "role": "user",
                "content": [
                    { "type": "input_text", "text": "first" },
                    { "type": "input_text", "text": "second" },
                ],
            },
        ]);
        assert_eq!(extract_responses_input(&input), "first\nsecond");
    }

    #[test]
    fn extract_responses_input_handles_string_content() {
        let input = json!([{ "role": "user", "content": "direct" }]);
        assert_eq!(extract_responses_input(&input), "direct");
    }

    #[test]
    fn extract_responses_input_unrecognised_yields_empty() {
        assert_eq!(extract_responses_input(&json!(123)), "");
        assert_eq!(extract_responses_input(&json!(null)), "");
    }
}
