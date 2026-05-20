---
name: Harden SSH Access
slug: harden-ssh
trigger: ssh, secure shell, ssh hardening, remote access
category: system
quality: 0.83
author: argo-team
license: MIT
requires_tools: [shell, file_write]
---

# Harden SSH Access

1. Disable password auth; require key-based authentication only.
2. Disable direct root login (`PermitRootLogin no`).
3. Restrict access to specific users or groups.
4. Add `fail2ban` or rate limiting against brute-force attempts.
5. Validate config with `sshd -t` before reloading, and keep one session open.
