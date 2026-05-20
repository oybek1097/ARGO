---
name: Audit Web Page Performance
slug: audit-page-performance
trigger: web performance, page speed, lighthouse, core web vitals
category: web
quality: 0.78
author: argo-team
license: MIT
requires_tools: [http_get]
---

# Audit Web Page Performance

1. Measure Core Web Vitals: LCP, CLS, and INP on a real device profile.
2. Identify the largest blocking resources in the waterfall.
3. Check for unoptimised images and render-blocking CSS/JS.
4. Recommend concrete fixes: compression, lazy-load, code-split, caching.
5. Re-measure after changes and report the before/after deltas.
