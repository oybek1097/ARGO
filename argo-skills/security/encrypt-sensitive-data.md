---
name: Encrypt Sensitive Data at Rest
slug: encrypt-sensitive-data
trigger: encryption, encrypt data, at rest, data protection
category: security
quality: 0.77
author: argo-team
license: MIT
requires_tools: [file_read, file_write]
---

# Encrypt Sensitive Data at Rest

1. Classify the data and decide what must be encrypted.
2. Use a vetted algorithm (AES-256-GCM) — never roll your own.
3. Store keys in a KMS or vault, separate from the ciphertext.
4. Plan key rotation and re-encryption ahead of time.
5. Verify backups and logs do not leak the plaintext.
