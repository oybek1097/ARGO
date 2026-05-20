---
name: Reclaim Disk Space
slug: free-disk-space
trigger: disk full, disk space, storage, cleanup
category: system
quality: 0.8
author: argo-team
license: MIT
requires_tools: [shell]
---

# Reclaim Disk Space

1. Find the biggest consumers with `du -sh /* | sort -h`.
2. Check for large logs, old packages, and orphaned temp files.
3. Rotate or truncate logs; prune Docker images and build caches.
4. Confirm nothing critical is deleted — verify before `rm`.
5. Add log rotation or a cleanup cron so it does not recur.
