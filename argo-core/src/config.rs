//! Configuration loader — environment variables only (spec section 4.1).
//!
//! A file-based loader (`~/.argo/config.yaml`) will be added alongside the
//! brain's config module in a later sprint.

/// Runtime configuration for argo-core.
#[derive(Clone, Debug)]
pub struct Config {
    /// Listen address for the HTTP gateway.
    pub host: String,
    /// Listen port for the HTTP gateway.
    pub port: u16,
    /// Path to the argo-brain IPC Unix socket.
    pub brain_socket: String,
    /// Crate version, baked in at compile time.
    pub version: &'static str,
}

impl Config {
    /// Builds the configuration from `ARGO_*` environment variables,
    /// falling back to sensible defaults.
    pub fn from_env() -> Self {
        let home = std::env::var("ARGO_HOME").unwrap_or_else(|_| {
            let base = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
            format!("{base}/.argo")
        });

        Self {
            host: std::env::var("ARGO_CORE_HOST")
                .unwrap_or_else(|_| "127.0.0.1".to_string()),
            port: std::env::var("ARGO_CORE_PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or(8000),
            brain_socket: std::env::var("ARGO_IPC_SOCKET")
                .unwrap_or_else(|_| format!("{home}/argo.sock")),
            version: env!("CARGO_PKG_VERSION"),
        }
    }
}
