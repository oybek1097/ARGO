---
name: Deploy to Kubernetes
slug: deploy-k8s
trigger: deploy, kubernetes, k8s, helm, rollout
category: devops
quality: 0.88
author: argo-team
license: MIT
requires_tools: [kubectl, helm_install, vault_get]
---

# Deploy to Kubernetes

When the user asks to deploy a service to a Kubernetes cluster:

1. Confirm the target cluster with `kubectl config current-context`.
2. Locate the deployment manifest — check `k8s/`, `manifests/`, or `helm/`.
3. Resolve required secrets from Vault with `vault_get` and create/update
   the matching `Secret` objects.
4. Apply changes with `kubectl apply -f` or `helm upgrade --install`.
5. Watch the rollout with `kubectl rollout status deployment/<name>`.
6. If the rollout stalls past its timeout, run `kubectl rollout undo`.
7. Report the final pod state and the external URL or ingress host.
