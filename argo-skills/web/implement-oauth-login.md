---
name: Implement OAuth Login
slug: implement-oauth-login
trigger: oauth, social login, sign in, authentication flow
category: web
quality: 0.77
author: argo-team
license: MIT
requires_tools: [file_write, http_get]
---

# Implement OAuth Login

1. Register the app with the provider; record client ID and secret.
2. Use the authorization-code flow with PKCE for public clients.
3. Validate the `state` parameter to prevent CSRF on the callback.
4. Exchange the code server-side; never expose the secret to the browser.
5. Store tokens securely and implement refresh before expiry.
