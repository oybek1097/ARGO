---
name: Audit Running Processes
slug: audit-running-processes
trigger: processes, audit, ps, what is running
category: system
quality: 0.72
author: argo-team
license: MIT
requires_tools: [shell]
---

# Audit Running Processes

1. List all processes with their owner, start time, and command.
2. Flag anything unexpected — unknown binaries or odd paths.
3. Check parent-child trees for suspicious spawns.
4. Cross-check listening sockets against expected services.
5. Investigate or terminate anything that cannot be accounted for.
