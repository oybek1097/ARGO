//! IPC client — spec section 3.4.
//!
//! argo-core talks to argo-brain over a Unix socket using line-delimited
//! JSON: one request line out, one response line in.

use serde_json::Value;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;

/// Sends one JSON request to the brain and returns its JSON response.
///
/// A fresh connection is opened per call; the brain closes it once the
/// response line has been written.
pub async fn call(socket: &str, request: &Value) -> Result<Value, String> {
    let stream = UnixStream::connect(socket)
        .await
        .map_err(|e| format!("brain unreachable ({socket}): {e}"))?;
    let (read_half, mut write_half) = stream.into_split();

    let mut line = serde_json::to_string(request).map_err(|e| e.to_string())?;
    line.push('\n');
    write_half
        .write_all(line.as_bytes())
        .await
        .map_err(|e| format!("ipc write failed: {e}"))?;
    write_half
        .flush()
        .await
        .map_err(|e| format!("ipc flush failed: {e}"))?;

    let mut reader = BufReader::new(read_half);
    let mut response = String::new();
    reader
        .read_line(&mut response)
        .await
        .map_err(|e| format!("ipc read failed: {e}"))?;

    if response.trim().is_empty() {
        return Err("empty response from brain".to_string());
    }
    serde_json::from_str(&response).map_err(|e| format!("bad brain response: {e}"))
}
