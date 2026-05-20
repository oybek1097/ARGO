---
name: Harden a Web Application
slug: harden-web-app
trigger: web security, harden, owasp, security headers
category: security
quality: 0.83
author: argo-team
license: MIT
requires_tools: [file_read, file_write]
---

# Harden a Web Application

1. Set security headers: CSP, HSTS, X-Content-Type-Options, frame-options.
2. Validate and encode all input and output to block injection and XSS.
3. Enforce authentication and authorisation on every sensitive route.
4. Use parameterised queries; never build SQL by string concatenation.
5. Keep dependencies patched and disable verbose error pages in production.
