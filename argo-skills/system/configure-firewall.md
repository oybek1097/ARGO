---
name: Configure a Host Firewall
slug: configure-firewall
trigger: firewall, iptables, ufw, network security
category: system
quality: 0.8
author: argo-team
license: MIT
requires_tools: [shell]
---

# Configure a Host Firewall

1. Start from default-deny for inbound traffic.
2. Allow only required ports (e.g. SSH, HTTP, HTTPS) explicitly.
3. Restrict management ports to known source IP ranges.
4. Allow established/related connections so responses flow.
5. Test from outside, then persist the rules across reboots.
