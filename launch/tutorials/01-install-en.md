# Tutorial 01 — Install ARGO in 5 minutes (English)

**Topic:** Installation
**Language:** English
**Target duration:** ~4 minutes

---

### Scene 1 — Intro (0:00–0:25)

ON SCREEN: ARGO logo, then a clean terminal window.

NARRATION: "Hi, and welcome to ARGO. ARGO is an open-source, self-hosted
AI agent platform. In the next few minutes we'll install it from scratch.
The good news: there's almost nothing to install — the ARGO brain runs on
the Python standard library alone."

### Scene 2 — Prerequisites (0:25–0:55)

ON SCREEN:
```
python3 --version
git --version
```

NARRATION: "You need two things: Python 3, and Git. That's it for trying
ARGO. If you want to build the Rust gateway later, you'll also need a
Rust toolchain — but we don't need it for this video."

### Scene 3 — Clone the repository (0:55–1:35)

ON SCREEN:
```
git clone https://github.com/argo-agent/argo.git
cd argo
```

NARRATION: "First, clone the repository and step into it. ARGO has two
parts: argo-core, the Rust gateway, and argo-brain, the Python brain.
We'll work with the brain for now."

### Scene 4 — Run the setup script (1:35–2:40)

ON SCREEN:
```
./scripts/setup.sh
```

NARRATION: "ARGO ships a one-shot setup script. It checks your toolchain,
builds argo-core if Rust is available, and configures sensible defaults.
If you'd rather do it by hand, you can run the interactive wizard
instead."

ON SCREEN:
```
cd argo-brain
python3 -m argo_brain setup
```

NARRATION: "The setup wizard walks you through the basic configuration
step by step."

### Scene 5 — Verify with doctor (2:40–3:25)

ON SCREEN:
```
python3 -m argo_brain doctor
```

NARRATION: "Now run the doctor command. This is ARGO's built-in
diagnostic — it checks your installation and reports anything that looks
wrong. If every line is green, you're ready."

### Scene 6 — First run (3:25–3:50)

ON SCREEN:
```
python3 -m argo_brain chat
```

NARRATION: "And to prove it works, start a chat. This runs against a
local mock model, so it needs no API key and no internet. Type a message,
and ARGO responds."

### Scene 7 — Closing / call to action (3:50–4:10)

ON SCREEN: ARGO logo, the GitHub URL, and "Next: Your first conversation".

NARRATION: "That's it — ARGO is installed. ARGO is open-source and MIT
licensed, and it's currently in alpha approaching general availability,
so your feedback genuinely helps. Star us on GitHub, and watch the next
video where we explore your first real conversation and the CLI. Thanks
for watching."
