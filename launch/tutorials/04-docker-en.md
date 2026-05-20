# Tutorial 04 — Deploying with Docker Compose (English)

**Topic:** Self-hosting ARGO with Docker Compose
**Language:** English
**Target duration:** ~5 minutes

---

### Scene 1 — Intro (0:00–0:25)

ON SCREEN: ARGO logo, then a terminal.

NARRATION: "Welcome to the final video in this series. We've installed
ARGO, chatted with it, and connected a Telegram bot. Now let's deploy it
the way you'd run it on a server — with Docker Compose."

### Scene 2 — The architecture (0:25–1:15)

ON SCREEN: a simple diagram —
```
[ argo-brain ]  <-- Unix socket -->  [ argo-core ]  --> port 8000
   Python brain      shared volume       Rust gateway
```

NARRATION: "ARGO's Docker setup has two services. argo-brain is the
Python brain — it runs the agent loop over a Unix socket. argo-core is
the Rust gateway — it exposes the HTTP API on port 8000 and talks to the
brain over that same socket. The compose file wires them together with
two shared volumes: one for the socket, one for persistent data."

### Scene 3 — Look at the compose file (1:15–2:15)

ON SCREEN: `docker-compose.yml` open, scrolling slowly.

NARRATION: "ARGO ships a ready docker-compose.yml at the repository
root. Notice both services agree on ARGO_IPC_SOCKET — that's the socket
path they share. The argo-data volume holds your SQLite database and
skills, so your data survives restarts. And argo-core has a health check
hitting the slash-api-slash-health endpoint."

### Scene 4 — Build and start (2:15–3:25)

ON SCREEN:
```
docker compose up -d --build
```

NARRATION: "From the repository root, run docker compose up. The
dash-d flag runs it in the background; dash-dash-build builds the images
the first time. Docker builds both the Python and Rust images and starts
the two containers."

ON SCREEN:
```
docker compose ps
```

NARRATION: "Check the status with docker compose ps. Wait until
argo-core reports healthy — that's the health check passing."

### Scene 5 — Verify the API (3:25–4:15)

ON SCREEN:
```
curl http://localhost:8000/api/health
```

NARRATION: "Now verify it from the host. A request to the health
endpoint should return an OK response. The gateway also exposes
slash-api-slash-chat for conversations and slash-metrics for Prometheus.
Your ARGO instance is now running as a proper self-hosted service."

### Scene 6 — Logs and lifecycle (4:15–4:45)

ON SCREEN:
```
docker compose logs -f
docker compose down
```

NARRATION: "Use docker compose logs to follow what each service is
doing, and docker compose down to stop everything. Your data stays
safe in the named volume, ready for the next time you start up."

### Scene 7 — Closing / call to action (4:45–5:05)

ON SCREEN: ARGO logo, GitHub URL, "Thanks for watching".

NARRATION: "That's ARGO, self-hosted with Docker Compose — entirely on
your own infrastructure. ARGO is open-source and MIT licensed, and it's
in alpha approaching general availability, so this is the best time to
get involved. Star the repo, file issues, and if you speak any of the
Central Asian languages, your corrections are especially welcome. Thanks
for watching the whole series."
