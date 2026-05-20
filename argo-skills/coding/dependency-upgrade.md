---
name: Upgrade a Project Dependency
slug: dependency-upgrade
trigger: upgrade dependency, bump version, update package
category: coding
quality: 0.77
author: argo-team
license: MIT
requires_tools: [shell, file_read]
---

# Upgrade a Project Dependency

1. Read the changelog between the current and target versions.
2. Note breaking changes and deprecations affecting your usage.
3. Bump the version in the manifest and regenerate the lockfile.
4. Run the full test suite and fix any breakages from the upgrade.
5. Check the dependency tree for newly introduced transitive risk.
