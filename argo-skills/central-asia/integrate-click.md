---
name: Integrate the Click Payment System
slug: integrate-click
trigger: click uzbekistan, click payment, uzcard payment
category: central-asia
quality: 0.82
author: argo-team
license: MIT
requires_tools: [http_get, file_write]
---

# Integrate the Click Payment System

1. Register with Click and obtain the service ID, merchant ID, and secret key.
2. Implement the two-step Prepare and Complete callback endpoints.
3. Verify the request signature (MD5 of the agreed parameter order).
4. Return the documented error codes for invalid or duplicate requests.
5. Persist each transaction with its Click transaction ID for reconciliation.
6. Verify the full flow in the test environment first.
