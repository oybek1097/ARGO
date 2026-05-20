# syntax=docker/dockerfile:1
# argo-brain — the ARGO Agent Python brain.
#
# The argo_brain package is stdlib-only, so no pip install is needed:
# we simply copy the package into a slim Python image and run the IPC server.

FROM python:3.12-slim AS runtime

# Run as an unprivileged user.
RUN useradd --system --create-home --uid 10002 argo

WORKDIR /app

# Copy the stdlib-only package. No dependency installation is required.
COPY argo_brain ./argo_brain

# ARGO_HOME holds both the IPC socket ($ARGO_HOME/argo.sock) and the
# data directory ($ARGO_HOME/data). It is backed by shared volumes so
# argo-core can reach the same socket and data files.
ENV ARGO_HOME=/data \
    PYTHONUNBUFFERED=1

# /run/argo holds the IPC socket; /data holds persistent data.
RUN mkdir -p /data /run/argo && chown -R argo:argo /app /data /run/argo

USER argo

# Run the IPC server (Unix socket); see argo_brain/__main__.py.
ENTRYPOINT ["python3", "-m", "argo_brain", "ipc"]
