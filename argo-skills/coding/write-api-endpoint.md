---
name: Implement a REST API Endpoint
slug: write-api-endpoint
trigger: api endpoint, rest, route, handler, http
category: coding
quality: 0.79
author: argo-team
license: MIT
requires_tools: [file_read, file_write]
---

# Implement a REST API Endpoint

1. Define the method, path, request schema, and response schema.
2. Validate and sanitise all input before any business logic.
3. Implement the handler; keep it thin and delegate to a service layer.
4. Return correct status codes and a consistent error envelope.
5. Add auth checks, rate-limit hooks, and tests for success and failure.
