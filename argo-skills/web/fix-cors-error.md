---
name: Fix a CORS Error
slug: fix-cors-error
trigger: cors, cross origin, preflight, access-control
category: web
quality: 0.8
author: argo-team
license: MIT
requires_tools: [http_get, file_read]
---

# Fix a CORS Error

1. Read the exact browser console message — origin, method, header.
2. Confirm whether the request is simple or triggers a preflight.
3. On the server, return `Access-Control-Allow-Origin` for the exact origin.
4. For preflights, also allow the requested methods and headers.
5. Never use a wildcard origin together with credentialed requests.
