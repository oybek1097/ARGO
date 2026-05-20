//! Pure, testable helper logic for the `argo` CLI.
//!
//! This module holds everything that does not perform I/O: argument
//! parsing into a [`Command`] enum and base-URL resolution. Keeping it
//! separate from `main.rs` makes the logic unit-testable.

/// Default base URL for the argo-core gateway.
pub const DEFAULT_BASE_URL: &str = "http://127.0.0.1:8000";

/// Name of the environment variable that overrides the gateway base URL.
pub const BASE_URL_ENV: &str = "ARGO_CORE_URL";

/// CLI version, taken from the crate's `Cargo.toml`.
pub const CLI_VERSION: &str = env!("CARGO_PKG_VERSION");

/// A parsed CLI invocation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Command {
    /// `argo health` — query the gateway liveness probe.
    Health,
    /// `argo chat <message>` — send a chat message.
    Chat { message: String },
    /// `argo history <user_id>` — fetch cached history for a user.
    History { user_id: String },
    /// `argo version` — print the CLI version.
    Version,
    /// `argo help` (or no args) — print usage.
    Help,
}

/// Parse the argument list (everything *after* the program name) into a
/// [`Command`].
///
/// Returns `Err` with a human-readable message on unknown or malformed
/// invocations.
pub fn parse_args<I, S>(args: I) -> Result<Command, String>
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    let args: Vec<String> = args.into_iter().map(|s| s.as_ref().to_string()).collect();

    let (sub, rest) = match args.split_first() {
        Some((sub, rest)) => (sub.as_str(), rest),
        None => return Ok(Command::Help),
    };

    match sub {
        "health" => Ok(Command::Health),
        "version" | "--version" | "-V" => Ok(Command::Version),
        "help" | "--help" | "-h" => Ok(Command::Help),
        "chat" => {
            if rest.is_empty() {
                return Err("`chat` requires a message: argo chat <message>".to_string());
            }
            // Join any extra words so unquoted messages still work.
            Ok(Command::Chat {
                message: rest.join(" "),
            })
        }
        "history" => match rest.first() {
            Some(uid) if !uid.is_empty() => Ok(Command::History {
                user_id: uid.clone(),
            }),
            _ => Err("`history` requires a user id: argo history <user_id>".to_string()),
        },
        other => Err(format!("unknown command: `{other}` (try `argo help`)")),
    }
}

/// Resolve the gateway base URL.
///
/// `env_value` is the value of `ARGO_CORE_URL` (use `std::env::var` at the
/// call site). A `None` or empty/whitespace value falls back to
/// [`DEFAULT_BASE_URL`]. Any trailing slash is trimmed so callers can append
/// paths like `/api/health` unconditionally.
pub fn resolve_base_url(env_value: Option<&str>) -> String {
    let raw = match env_value {
        Some(v) if !v.trim().is_empty() => v.trim(),
        _ => DEFAULT_BASE_URL,
    };
    raw.trim_end_matches('/').to_string()
}

/// Build a full URL by joining the (already normalised) base URL with a path.
///
/// `path` is expected to start with `/`; if it does not, one is inserted.
pub fn build_url(base: &str, path: &str) -> String {
    let base = base.trim_end_matches('/');
    if path.starts_with('/') {
        format!("{base}{path}")
    } else {
        format!("{base}/{path}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_health() {
        assert_eq!(parse_args(["health"]).unwrap(), Command::Health);
    }

    #[test]
    fn parses_version_aliases() {
        assert_eq!(parse_args(["version"]).unwrap(), Command::Version);
        assert_eq!(parse_args(["--version"]).unwrap(), Command::Version);
        assert_eq!(parse_args(["-V"]).unwrap(), Command::Version);
    }

    #[test]
    fn no_args_is_help() {
        let empty: [&str; 0] = [];
        assert_eq!(parse_args(empty).unwrap(), Command::Help);
        assert_eq!(parse_args(["help"]).unwrap(), Command::Help);
        assert_eq!(parse_args(["-h"]).unwrap(), Command::Help);
    }

    #[test]
    fn parses_chat_single_word() {
        assert_eq!(
            parse_args(["chat", "hello"]).unwrap(),
            Command::Chat {
                message: "hello".to_string()
            }
        );
    }

    #[test]
    fn parses_chat_joins_multiple_words() {
        assert_eq!(
            parse_args(["chat", "hello", "there", "argo"]).unwrap(),
            Command::Chat {
                message: "hello there argo".to_string()
            }
        );
    }

    #[test]
    fn chat_without_message_errors() {
        assert!(parse_args(["chat"]).is_err());
    }

    #[test]
    fn parses_history() {
        assert_eq!(
            parse_args(["history", "u-42"]).unwrap(),
            Command::History {
                user_id: "u-42".to_string()
            }
        );
    }

    #[test]
    fn history_without_uid_errors() {
        assert!(parse_args(["history"]).is_err());
    }

    #[test]
    fn unknown_command_errors() {
        assert!(parse_args(["frobnicate"]).is_err());
    }

    #[test]
    fn base_url_defaults_when_unset() {
        assert_eq!(resolve_base_url(None), DEFAULT_BASE_URL);
    }

    #[test]
    fn base_url_defaults_when_blank() {
        assert_eq!(resolve_base_url(Some("   ")), DEFAULT_BASE_URL);
        assert_eq!(resolve_base_url(Some("")), DEFAULT_BASE_URL);
    }

    #[test]
    fn base_url_uses_env_and_trims_slash() {
        assert_eq!(
            resolve_base_url(Some("http://example.com:9000/")),
            "http://example.com:9000"
        );
        assert_eq!(
            resolve_base_url(Some("  http://host:1/  ")),
            "http://host:1"
        );
    }

    #[test]
    fn build_url_joins_paths() {
        assert_eq!(
            build_url("http://h:8000", "/api/health"),
            "http://h:8000/api/health"
        );
        assert_eq!(
            build_url("http://h:8000/", "/api/health"),
            "http://h:8000/api/health"
        );
        assert_eq!(
            build_url("http://h:8000", "api/health"),
            "http://h:8000/api/health"
        );
    }
}
