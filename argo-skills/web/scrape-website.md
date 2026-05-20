---
name: Scrape Data from a Website
slug: scrape-website
trigger: scrape, web scraping, crawl, extract web data
category: web
quality: 0.79
author: argo-team
license: MIT
requires_tools: [http_get, file_write]
---

# Scrape Data from a Website

1. Check `robots.txt` and the site's terms before scraping.
2. Fetch one page and inspect the HTML structure of the target data.
3. Write selectors (CSS/XPath) for the fields and test on that page.
4. Add polite delays and a descriptive User-Agent; handle pagination.
5. Validate extracted rows, then store with the source URL and timestamp.
