---
name: Find and Fix Broken Links
slug: debug-broken-link
trigger: broken link, 404, dead link, link checker
category: web
quality: 0.71
author: argo-team
license: MIT
requires_tools: [http_get]
---

# Find and Fix Broken Links

1. Crawl the site and record every link with its response status.
2. Group failures: 404 not found, 5xx, and redirect chains.
3. For each 404, find the intended target or the nearest live page.
4. Fix internal links at the source; add redirects for changed URLs.
5. Re-crawl to confirm zero broken links remain.
