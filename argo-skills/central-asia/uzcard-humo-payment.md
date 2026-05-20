---
name: Accept UzCard and Humo Cards
slug: uzcard-humo-payment
trigger: uzcard, humo, local card, uzbekistan card payment
category: central-asia
quality: 0.79
author: argo-team
license: MIT
requires_tools: [http_get]
---

# Accept UzCard and Humo Cards

1. Determine the card network from the card BIN prefix.
2. Route the transaction through the appropriate processing gateway.
3. Handle the OTP confirmation step required for local cards.
4. Store only tokenised card references — never the raw PAN.
5. Reconcile settlements daily against the processor report.
