---
name: Configure an Nginx Reverse Proxy
slug: setup-nginx-reverse-proxy
trigger: nginx, reverse proxy, proxy_pass, web server
category: devops
quality: 0.79
author: argo-team
license: MIT
requires_tools: [shell, file_write]
---

# Configure an Nginx Reverse Proxy

1. Create a server block with the target `server_name` and listen ports.
2. Add a `location /` block with `proxy_pass` to the upstream address.
3. Forward `Host`, `X-Real-IP`, and `X-Forwarded-For` / `-Proto` headers.
4. Set sane `proxy_read_timeout` and enable `gzip` for text responses.
5. Validate config with `nginx -t`, then reload with `nginx -s reload`.
6. Verify the proxy end to end with a curl request.
