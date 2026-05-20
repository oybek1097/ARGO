---
name: Exchange E-Documents via Didox
slug: didox-edi
trigger: didox, edi uzbekistan, electronic document, e-invoice
category: central-asia
quality: 0.72
author: argo-team
license: MIT
requires_tools: [http_get, file_write]
---

# Exchange E-Documents via Didox

1. Authenticate to the Didox API with the company credentials.
2. Build the document (contract, invoice, act) in the required schema.
3. Sign it with the organisation's electronic digital signature (EDS/ERI).
4. Send it to the counterparty and track its acceptance status.
5. Archive the signed document and its confirmation locally.
