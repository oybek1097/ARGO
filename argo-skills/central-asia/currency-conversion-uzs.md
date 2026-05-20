---
name: Handle UZS Currency Conversion
slug: currency-conversion-uzs
trigger: uzs, som, currency conversion, exchange rate uzbekistan
category: central-asia
quality: 0.7
author: argo-team
license: MIT
requires_tools: [http_get]
---

# Handle UZS Currency Conversion

1. Fetch the official rate from the Central Bank of Uzbekistan API.
2. Cache the daily rate; it updates once per business day.
3. Convert amounts using integer minor units to avoid float drift.
4. Round per accounting rules and display with the soʻm symbol.
5. Record the rate used with every converted transaction.
