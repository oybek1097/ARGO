---
name: Schedule a Reliable Cron Job
slug: schedule-cron-job
trigger: cron, scheduled task, cron job, periodic
category: system
quality: 0.76
author: argo-team
license: MIT
requires_tools: [shell, file_write]
---

# Schedule a Reliable Cron Job

1. Write the command as a script; cron has a minimal environment.
2. Use absolute paths and set required environment variables explicitly.
3. Redirect stdout/stderr to a log file for debugging.
4. Add a lock to prevent overlapping runs of a slow job.
5. Emit a heartbeat so a silent failure is detectable.
