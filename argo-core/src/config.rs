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

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    /// `Config::from_env` reads process-wide env vars; this serialises the
    /// tests that mutate them so they don't race each other.
    static ENV_LOCK: Mutex<()> = Mutex::new(());

    /// Clears every variable `Config::from_env` consults.
    fn clear_env() {
        for key in ["ARGO_HOME", "HOME", "ARGO_CORE_HOST", "ARGO_CORE_PORT", "ARGO_IPC_SOCKET"] {
            std::env::remove_var(key);
        }
    }

    #[test]
    fn from_env_uses_defaults_when_unset() {
        let _guard = ENV_LOCK.lock().unwrap();
        clear_env();
        std::env::set_var("HOME", "/tmp/argo-test-home");

        let config = Config::from_env();
        assert_eq!(config.host, "127.0.0.1");
        assert_eq!(config.port, 8000);
        assert_eq!(config.brain_socket, "/tmp/argo-test-home/.argo/argo.sock");
        assert_eq!(config.version, env!("CARGO_PKG_VERSION"));
    }

    #[test]
    fn from_env_applies_overrides() {
        let _guard = ENV_LOCK.lock().unwrap();
        clear_env();
        std::env::set_var("ARGO_CORE_HOST", "0.0.0.0");
        std::env::set_var("ARGO_CORE_PORT", "9999");
        std::env::set_var("ARGO_IPC_SOCKET", "/run/argo/custom.sock");

        let config = Config::from_env();
        assert_eq!(config.host, "0.0.0.0");
        assert_eq!(config.port, 9999);
        assert_eq!(config.brain_socket, "/run/argo/custom.sock");

        clear_env();
    }

    #[test]
    fn from_env_argo_home_drives_socket_default() {
        let _guard = ENV_LOCK.lock().unwrap();
        clear_env();
        std::env::set_var("ARGO_HOME", "/opt/argo");

        let config = Config::from_env();
        assert_eq!(config.brain_socket, "/opt/argo/argo.sock");

        clear_env();
    }

    #[test]
    fn from_env_ignores_invalid_port() {
        let _guard = ENV_LOCK.lock().unwrap();
        clear_env();
        std::env::set_var("ARGO_CORE_PORT", "not-a-number");

        let config = Config::from_env();
        // An unparseable port falls back to the default.
        assert_eq!(config.port, 8000);

        clear_env();
    }
}
