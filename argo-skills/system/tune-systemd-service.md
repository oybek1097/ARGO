---
name: Create a Robust systemd Service
slug: tune-systemd-service
trigger: systemd, service, daemon, unit file
category: system
quality: 0.75
author: argo-team
license: MIT
requires_tools: [file_write, shell]
---

# Create a Robust systemd Service

1. Write a unit with `ExecStart`, the working directory, and the user.
2. Set `Restart=on-failure` with a sane `RestartSec` backoff.
3. Add resource limits (`MemoryMax`, `CPUQuota`) to contain runaway use.
4. Set `WantedBy` so it starts on boot; declare ordering dependencies.
5. `daemon-reload`, enable, start, and verify with `systemctl status`.
