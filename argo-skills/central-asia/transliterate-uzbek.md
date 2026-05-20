---
name: Transliterate Between Uzbek Scripts
slug: transliterate-uzbek
trigger: transliterate, uzbek latin cyrillic, script conversion
category: central-asia
quality: 0.74
author: argo-team
license: MIT
requires_tools: [file_read, file_write]
---

# Transliterate Between Uzbek Scripts

1. Detect the source script (Latin Uzbek or Cyrillic Uzbek).
2. Apply the official transliteration mapping in the chosen direction.
3. Handle the special letters: oʻ, gʻ, sh, ch, ng correctly.
4. Preserve proper nouns, numbers, and punctuation.
5. Spot-check output with a native-text sample before bulk conversion.
