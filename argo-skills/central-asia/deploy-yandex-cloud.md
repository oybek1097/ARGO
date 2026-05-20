---
name: Deploy to Yandex Cloud
slug: deploy-yandex-cloud
trigger: yandex cloud, yandex, cloud deploy, cis cloud
category: central-asia
quality: 0.82
author: argo-team
license: MIT
requires_tools: [shell, http_get]
---

# Deploy to Yandex Cloud

1. Authenticate the `yc` CLI and select the target folder and cloud.
2. Pick a region — use `ru-central1` for Russia/CIS data residency.
3. Provision the compute or managed service with `yc` or Terraform.
4. Configure security groups; expose only required ports.
5. Deploy the workload and verify via the service endpoint.
6. Set up Yandex Monitoring alerts before declaring the deploy done.
