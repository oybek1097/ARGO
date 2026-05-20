# syntax=docker/dockerfile:1
# argo-core — multi-stage build for the ARGO Agent Rust gateway.
#
# Stage 1 compiles the release binary; stage 2 ships a minimal Debian-slim
# runtime image containing only the stripped binary.

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM rust:1.82-slim AS builder

WORKDIR /build

# Copy the crate manifest and sources, then build the release binary.
# The release profile (see Cargo.toml) produces a small, stripped binary.
COPY Cargo.toml ./
COPY src ./src

RUN cargo build --release && \
    # Sanity-check that the expected binary was produced.
    test -x target/release/argo-core

# ---------------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------------
FROM debian:bookworm-slim AS runtime

# ca-certificates is handy for any outbound TLS; curl is used by the
# container healthcheck (see docker-compose.yml / Helm chart).
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Run as an unprivileged user.
RUN useradd --system --create-home --uid 10001 argo

# Copy only the compiled binary from the builder stage.
COPY --from=builder /build/target/release/argo-core /usr/local/bin/argo-core

# Shared location for the IPC socket and persistent data.
# ARGO_HOME is honoured by both argo-core and argo-brain; the brain places
# its socket at $ARGO_HOME/argo.sock, which argo-core reads via ARGO_IPC_SOCKET.
ENV ARGO_HOME=/data \
    ARGO_CORE_HOST=0.0.0.0 \
    ARGO_CORE_PORT=8000 \
    ARGO_IPC_SOCKET=/run/argo/argo.sock

RUN mkdir -p /data /run/argo && chown -R argo:argo /data /run/argo

USER argo

# HTTP gateway port.
EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/argo-core"]
