---
name: Configure API Rate Limiting
slug: configure-rate-limiting
trigger: rate limit, throttling, abuse prevention, api limits
category: security
quality: 0.74
author: argo-team
license: MIT
requires_tools: [file_write]
---

# Configure API Rate Limiting

1. Choose the dimension: per user, per IP, or per API key.
2. Pick an algorithm — token bucket suits bursty traffic.
3. Set limits from real usage data plus headroom.
4. Return `429` with a `Retry-After` header on rejection.
5. Monitor rejection rates and exempt critical internal callers.
