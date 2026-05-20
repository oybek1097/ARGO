---
name: Audit Web Accessibility
slug: accessibility-audit
trigger: accessibility, a11y, wcag, screen reader
category: web
quality: 0.73
author: argo-team
license: MIT
requires_tools: [http_get, file_read]
---

# Audit Web Accessibility

1. Run an automated checker, then verify findings manually.
2. Confirm keyboard-only navigation reaches every interactive element.
3. Check colour contrast meets WCAG AA for text and UI components.
4. Verify images have alt text and form fields have labels.
5. Test with a screen reader on the primary user flow.
