---
name: Send SMS via an Uzbek SMS Gateway
slug: sms-gateway-uz
trigger: sms uzbekistan, eskiz, playmobile, sms gateway
category: central-asia
quality: 0.76
author: argo-team
license: MIT
requires_tools: [http_get]
---

# Send SMS via an Uzbek SMS Gateway

1. Obtain an API token from the provider (e.g. Eskiz or Play Mobile).
2. Register the sender name (alphanumeric ID) with the provider first.
3. Format the recipient number in international form (998XXXXXXXXX).
4. Submit the message; for templated content, use a pre-approved template.
5. Poll or receive the delivery callback and record the final status.
