---
name: Integrate the Payme Payment System
slug: integrate-payme
trigger: payme, payment uzbekistan, uzbek payment, merchant
category: central-asia
quality: 0.83
author: argo-team
license: MIT
requires_tools: [http_get, file_write]
---

# Integrate the Payme Payment System

1. Register a merchant account and obtain the cashbox key.
2. Implement the Payme Merchant API JSON-RPC endpoint.
3. Handle the required methods: CheckPerformTransaction, CreateTransaction,
   PerformTransaction, CancelTransaction, CheckTransaction.
4. Validate the Basic auth header against the merchant key on every call.
5. Make transaction state changes idempotent and persisted.
6. Test in the sandbox before switching to production credentials.
