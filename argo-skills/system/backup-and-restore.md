---
name: Set Up Backups and Test Restore
slug: backup-and-restore
trigger: backup, restore, snapshot, disaster recovery
category: system
quality: 0.82
author: argo-team
license: MIT
requires_tools: [shell]
---

# Set Up Backups and Test Restore

1. Define what to back up, the schedule, and the retention period.
2. Automate backups and store a copy off-host (3-2-1 rule).
3. Encrypt backups at rest and verify their integrity after each run.
4. Perform a full restore drill — an untested backup is not a backup.
5. Document the restore steps and the measured recovery time.
