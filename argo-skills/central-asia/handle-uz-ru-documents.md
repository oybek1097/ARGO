---
name: Process Uzbek and Russian Documents
slug: handle-uz-ru-documents
trigger: uzbek document, russian document, cyrillic, uz ru text
category: central-asia
quality: 0.78
author: argo-team
license: MIT
requires_tools: [file_read, file_write]
---

# Process Uzbek and Russian Documents

1. Detect the encoding; ensure UTF-8 and handle Cyrillic plus Latin Uzbek.
2. Account for both the Latin and Cyrillic Uzbek alphabets in matching.
3. Normalise dates to ISO 8601 — local formats are usually DD.MM.YYYY.
4. For OCR, select a model that supports Uzbek and Russian.
5. Preserve the original document alongside the extracted structured data.
