---
name: Resolve a Git Merge Conflict
slug: git-resolve-merge-conflict
trigger: merge conflict, git conflict, rebase conflict
category: coding
quality: 0.8
author: argo-team
license: MIT
requires_tools: [shell, file_read, file_write]
---

# Resolve a Git Merge Conflict

1. Run `git status` to list every conflicted file.
2. For each file, understand both sides — `git log` the two branches.
3. Edit the conflict markers to a correct combined result, not a blind pick.
4. Build and run tests before staging the resolution.
5. `git add` the resolved files and continue the merge or rebase.
