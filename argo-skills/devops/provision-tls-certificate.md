---
name: Provision a TLS Certificate
slug: provision-tls-certificate
trigger: tls, ssl, certificate, https, letsencrypt
category: devops
quality: 0.81
author: argo-team
license: MIT
requires_tools: [shell]
---

# Provision a TLS Certificate

1. Confirm DNS for the domain already points at this host.
2. Issue the certificate with `certbot --nginx -d <domain>` (or DNS-01 for
   wildcards).
3. Verify the chain and expiry with `openssl s_client -connect <domain>:443`.
4. Confirm auto-renewal is scheduled (`certbot renew --dry-run`).
5. Enable HSTS only after confirming all subresources load over HTTPS.
