---
name: Generate an Uzbek VAT Invoice
slug: uzbek-tax-invoice
trigger: uzbek tax, vat invoice, schyot faktura, soliq
category: central-asia
quality: 0.77
author: argo-team
license: MIT
requires_tools: [file_write]
---

# Generate an Uzbek VAT Invoice

1. Collect seller and buyer INN/STIR identifiers and bank details.
2. Itemise goods/services with quantity, unit price, and VAT rate.
3. Compute VAT at the current statutory rate and the gross total.
4. Format per the electronic invoice (schyot-faktura) requirements.
5. Submit to the tax portal and store the confirmation reference.
