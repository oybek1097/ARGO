---
name: Investigate via Aggregated Logs
slug: log-aggregation-query
trigger: logs, grep logs, loki, elasticsearch, kibana
category: devops
quality: 0.77
author: argo-team
license: MIT
requires_tools: [http_get, shell]
---

# Investigate via Aggregated Logs

1. Define the time window and the service/namespace to search.
2. Start broad: count log lines by level to spot an error spike.
3. Drill into the spike by filtering on a request ID or error message.
4. Correlate across services using a shared trace or correlation ID.
5. Extract the smallest reproducing case and summarise the failure path.
