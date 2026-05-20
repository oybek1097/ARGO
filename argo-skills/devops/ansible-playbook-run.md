---
name: Run an Ansible Playbook Safely
slug: ansible-playbook-run
trigger: ansible, playbook, configuration management
category: devops
quality: 0.76
author: argo-team
license: MIT
requires_tools: [shell]
---

# Run an Ansible Playbook Safely

1. Lint the playbook with `ansible-lint` and fix high-severity issues.
2. Run `--check --diff` against a single canary host first.
3. Review the diff; confirm no unintended service restarts.
4. Apply to the canary, verify, then roll out with `--limit` batches.
5. Record the run in change management with the host list and outcome.
