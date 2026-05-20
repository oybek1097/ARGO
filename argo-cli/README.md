# argo-cli

A lightweight blocking command-line client for the **argo-core** gateway.

The crate builds a single binary named `argo`.

## Build

```sh
cargo build --release
# binary at target/release/argo
```

## Usage

```sh
argo health              # GET /api/health  — prints status + version + uptime
argo chat <message>      # POST /api/chat   — prints the reply content
argo history <user_id>   # GET /api/history/:uid — prints cached message history
argo version             # prints the CLI version
argo help                # shows usage
```

Multi-word chat messages can be passed unquoted; the words are joined:

```sh
argo chat hello there argo
```

## Configuration

The gateway base URL is read from the `ARGO_CORE_URL` environment variable.
If unset (or blank) it defaults to `http://127.0.0.1:8000`.

```sh
ARGO_CORE_URL=http://gateway.internal:8000 argo health
```

## Tests

Pure helper logic (argument parsing and URL resolution) lives in `src/lib.rs`
and is covered by unit tests:

```sh
cargo test
```
