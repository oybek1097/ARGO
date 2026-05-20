---
name: Manage Environment Configuration
slug: manage-environment-variables
trigger: environment variables, env, config, dotenv
category: system
quality: 0.71
author: argo-team
license: MIT
requires_tools: [file_read, file_write]
---

# Manage Environment Configuration

1. Separate config from code — never hardcode environment values.
2. Keep a checked-in `.env.example` documenting every variable.
3. Keep real secrets out of version control.
4. Validate that all required variables are set at startup; fail fast.
5. Document each variable's purpose, default, and valid range.
