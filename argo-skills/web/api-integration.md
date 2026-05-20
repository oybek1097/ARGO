---
name: Integrate a Third-Party API
slug: api-integration
trigger: api integration, third party, external api, webhook
category: web
quality: 0.75
author: argo-team
license: MIT
requires_tools: [http_get, file_write]
---

# Integrate a Third-Party API

1. Read the API docs: auth, rate limits, pagination, and error format.
2. Store credentials in config/secrets, never in code.
3. Wrap calls in a client with retries, timeouts, and backoff.
4. Handle and surface API errors distinctly from your own.
5. Add a thin integration test against a sandbox or recorded fixture.
