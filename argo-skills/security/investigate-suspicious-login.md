---
name: Investigate a Suspicious Login
slug: investigate-suspicious-login
trigger: suspicious login, unauthorized access, intrusion
category: security
quality: 0.81
author: argo-team
license: MIT
requires_tools: [shell]
---

# Investigate a Suspicious Login

1. Collect the login's time, source IP, geolocation, and device.
2. Compare against the user's normal pattern.
3. Check what was accessed or changed during the session.
4. If confirmed malicious, revoke sessions and reset credentials.
5. Preserve logs, document a timeline, and check for lateral movement.
