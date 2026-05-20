//! `argo` — a small blocking command-line client for the argo-core gateway.
//!
//! See `lib.rs` for the pure (testable) argument-parsing and URL logic.

use std::process::ExitCode;

use argo_cli::{
    build_url, parse_args, resolve_base_url, Command, BASE_URL_ENV, CLI_VERSION, DEFAULT_BASE_URL,
};
use serde_json::{json, Value};

fn main() -> ExitCode {
    // Skip argv[0] (the program name); parse the rest by hand.
    let args: Vec<String> = std::env::args().skip(1).collect();

    let command = match parse_args(&args) {
        Ok(cmd) => cmd,
        Err(msg) => {
            eprintln!("error: {msg}");
            return ExitCode::FAILURE;
        }
    };

    let base = resolve_base_url(std::env::var(BASE_URL_ENV).ok().as_deref());

    let result = match command {
        Command::Help => {
            print_usage();
            return ExitCode::SUCCESS;
        }
        Command::Version => {
            println!("argo {CLI_VERSION}");
            return ExitCode::SUCCESS;
        }
        Command::Health => run_health(&base),
        Command::Chat { message } => run_chat(&base, &message),
        Command::History { user_id } => run_history(&base, &user_id),
    };

    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(msg) => {
            eprintln!("error: {msg}");
            ExitCode::FAILURE
        }
    }
}

/// Print CLI usage to stdout.
fn print_usage() {
    println!(
        "argo {CLI_VERSION} — command-line client for the argo-core gateway

USAGE:
    argo <command> [args]

COMMANDS:
    health              Check gateway health (status + version)
    chat <message>      Send a chat message and print the reply
    history <user_id>   Print cached message history for a user
    version             Print the CLI version
    help                Show this help

ENVIRONMENT:
    {BASE_URL_ENV}   Gateway base URL (default: {DEFAULT_BASE_URL})"
    );
}

/// Perform a GET request and decode the JSON body.
fn get_json(url: &str) -> Result<Value, String> {
    match ureq::get(url).call() {
        Ok(resp) => resp
            .into_json::<Value>()
            .map_err(|e| format!("invalid JSON response: {e}")),
        Err(ureq::Error::Status(code, resp)) => {
            let body = resp.into_string().unwrap_or_default();
            Err(format!("gateway returned HTTP {code}: {body}"))
        }
        Err(ureq::Error::Transport(t)) => Err(format!(
            "could not reach gateway at {url}: {t}"
        )),
    }
}

/// Perform a POST request with a JSON body and decode the JSON response.
fn post_json(url: &str, body: &Value) -> Result<Value, String> {
    match ureq::post(url).send_json(body) {
        Ok(resp) => resp
            .into_json::<Value>()
            .map_err(|e| format!("invalid JSON response: {e}")),
        Err(ureq::Error::Status(code, resp)) => {
            let body = resp.into_string().unwrap_or_default();
            Err(format!("gateway returned HTTP {code}: {body}"))
        }
        Err(ureq::Error::Transport(t)) => Err(format!(
            "could not reach gateway at {url}: {t}"
        )),
    }
}

/// `argo health` — GET /api/health.
fn run_health(base: &str) -> Result<(), String> {
    let url = build_url(base, "/api/health");
    let body = get_json(&url)?;
    let status = body
        .get("status")
        .and_then(Value::as_str)
        .unwrap_or("unknown");
    let version = body
        .get("version")
        .and_then(Value::as_str)
        .unwrap_or("unknown");
    let uptime = body.get("uptime_s").and_then(Value::as_u64);
    match uptime {
        Some(s) => println!("status: {status}  version: {version}  uptime: {s}s"),
        None => println!("status: {status}  version: {version}"),
    }
    Ok(())
}

/// `argo chat <message>` — POST /api/chat.
fn run_chat(base: &str, message: &str) -> Result<(), String> {
    let url = build_url(base, "/api/chat");
    let request = json!({
        "user_id": "cli",
        "message": message,
    });
    let body = post_json(&url, &request)?;
    // The brain reply carries a `content` field; fall back to the raw body.
    match body.get("content").and_then(Value::as_str) {
        Some(content) => println!("{content}"),
        None => println!("{body}"),
    }
    Ok(())
}

/// `argo history <user_id>` — GET /api/history/:uid.
fn run_history(base: &str, user_id: &str) -> Result<(), String> {
    let url = build_url(base, &format!("/api/history/{user_id}"));
    let body = get_json(&url)?;
    match body.get("history").and_then(Value::as_array) {
        Some(entries) if !entries.is_empty() => {
            for entry in entries {
                let role = entry.get("role").and_then(Value::as_str).unwrap_or("?");
                let content = entry
                    .get("content")
                    .and_then(Value::as_str)
                    .unwrap_or("");
                println!("[{role}] {content}");
            }
        }
        Some(_) => println!("(no history for {user_id})"),
        None => println!("{body}"),
    }
    Ok(())
}
