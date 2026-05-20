---
name: Diagnose a Network Connectivity Issue
slug: analyze-network-issue
trigger: network, connectivity, dns, latency, packet loss
category: system
quality: 0.77
author: argo-team
license: MIT
requires_tools: [shell]
---

# Diagnose a Network Connectivity Issue

1. Isolate the layer: DNS, routing, firewall, or the application.
2. Test name resolution with `dig`/`nslookup`.
3. Test reachability with `ping` and the path with `traceroute`/`mtr`.
4. Test the port specifically with `nc -vz host port`.
5. Inspect packets with `tcpdump` only once the layer is narrowed.
