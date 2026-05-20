---
name: Set Up Log Rotation
slug: rotate-logs
trigger: log rotation, logrotate, log files, disk logs
category: system
quality: 0.7
author: argo-team
license: MIT
requires_tools: [file_write, shell]
---

# Set Up Log Rotation

1. Identify which log files grow and how fast.
2. Configure rotation by size or time with a retention count.
3. Compress rotated logs to save space.
4. Signal the writing process to reopen its log file after rotation.
5. Verify with a forced rotation that nothing breaks.
