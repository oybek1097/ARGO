---
name: Review a Terraform Plan
slug: terraform-plan-review
trigger: terraform, infrastructure, plan, iac
category: devops
quality: 0.83
author: argo-team
license: MIT
requires_tools: [shell]
---

# Review a Terraform Plan

1. Run `terraform plan -out=tfplan` and then `terraform show -json tfplan`.
2. Summarise resources to add, change, and destroy — flag every destroy.
3. Check for in-place replacements that imply downtime (e.g. instance recreate).
4. Verify no secrets are written into state in plaintext.
5. Confirm the plan targets the intended workspace and backend.
6. Only apply after the user explicitly approves the destroy/replace list.
