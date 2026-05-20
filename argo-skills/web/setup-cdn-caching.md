---
name: Configure CDN Caching
slug: setup-cdn-caching
trigger: cdn, caching, cache headers, edge
category: web
quality: 0.7
author: argo-team
license: MIT
requires_tools: [http_get, file_read]
---

# Configure CDN Caching

1. Classify assets: immutable (hashed) vs dynamic vs personalised.
2. Set long `Cache-Control: immutable` for hashed static assets.
3. Use short TTLs or `stale-while-revalidate` for semi-dynamic pages.
4. Mark personalised responses `private, no-store`.
5. Verify cache HIT/MISS headers and purge correctly on deploy.
