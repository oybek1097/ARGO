---
name: Integrate OneID Government Authentication
slug: oneid-auth
trigger: oneid, one id, government login, uzbekistan auth
category: central-asia
quality: 0.73
author: argo-team
license: MIT
requires_tools: [http_get]
---

# Integrate OneID Government Authentication

1. Register the application and obtain the OneID client credentials.
2. Implement the OAuth2 authorization-code flow against OneID.
3. Validate the `state` parameter and exchange the code server-side.
4. Request only the user scopes the application actually needs.
5. Map the returned profile (PINFL and identity fields) to a local account.
