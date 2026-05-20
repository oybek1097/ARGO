---
name: Add a Real-Time WebSocket Feature
slug: websocket-realtime
trigger: websocket, realtime, live updates, socket
category: web
quality: 0.69
author: argo-team
license: MIT
requires_tools: [file_write]
---

# Add a Real-Time WebSocket Feature

1. Define the message schema and event types both directions.
2. Authenticate the connection on upgrade, not just on first message.
3. Handle reconnection with backoff and resume from the last event ID.
4. Apply heartbeats to detect dead connections.
5. Cap per-connection message rate to prevent abuse.
