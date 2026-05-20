# Tutorial 02 — Your first conversation & the CLI (English)

**Topic:** First conversation and the command-line interface
**Language:** English
**Target duration:** ~5 minutes

---

### Scene 1 — Intro (0:00–0:25)

ON SCREEN: ARGO logo, then a terminal.

NARRATION: "Welcome back. In the last video we installed ARGO. Now let's
actually use it — we'll have our first conversation, look at the
command-line interface, and see how ARGO detects languages."

### Scene 2 — The CLI overview (0:25–1:05)

ON SCREEN:
```
python3 -m argo_brain --help
```

ON SCREEN (highlight the listed commands):
```
setup     doctor    chat      tui
serve     ipc       telegram  mcp
selftest  version
```

NARRATION: "ARGO has one entry point — the argo_brain module — with a
handful of subcommands. We've already used setup and doctor. Today the
star is chat. There's also serve for the HTTP gateway, telegram for a
Telegram bot, and tui for a richer terminal interface."

### Scene 3 — Starting a chat (1:05–1:45)

ON SCREEN:
```
python3 -m argo_brain chat
```

NARRATION: "Run the chat command. This opens an interactive session.
By default it uses a local mock model, so no API key is needed — perfect
for learning how the agent behaves. Let's say hello."

ON SCREEN (typed by the user):
```
> Hello, what can you do?
```

NARRATION: "ARGO replies, and you can keep the conversation going."

### Scene 4 — Multilingual conversation (1:45–2:55)

ON SCREEN (typed by the user):
```
> Salom! Bugun ob-havo qanday?
```

NARRATION: "Here's the part ARGO is built for. I typed that in Uzbek.
ARGO detects the language and routes the response back in the same
language. Let's try Russian too."

ON SCREEN (typed by the user):
```
> Привет! Расскажи о себе.
```

NARRATION: "Russian works the same way. ARGO supports Uzbek, Russian,
Kazakh, Kyrgyz, Tajik, and English — language detection is built in, not
bolted on."

### Scene 5 — The agent loop and tools (2:55–4:00)

ON SCREEN (typed by the user):
```
> What files are in the current directory?
```

NARRATION: "ARGO isn't just a chatbot — it's an agent. When a request
needs an action, ARGO plans, then executes a tool, then uses the result.
This is the Plan-then-Execute loop. ARGO ships 13 built-in tools today,
including shell, files, Git, and Docker."

ON SCREEN: the agent showing a tool step, then the answer.

NARRATION: "You can see the tool step here, then the final answer built
from the result."

### Scene 6 — Memory (4:00–4:35)

ON SCREEN (typed by the user):
```
> My name is Aziz.
> What is my name?
```

NARRATION: "ARGO remembers within a conversation. It keeps a short-term
memory in process, and a longer-term store in a local SQLite database on
your own disk — your history never leaves your machine."

### Scene 7 — Closing / call to action (4:35–5:00)

ON SCREEN: ARGO logo, GitHub URL, "Next: Connecting a Telegram bot".

NARRATION: "That's your first ARGO conversation, the CLI, multilingual
replies, tools, and memory. ARGO is open-source, MIT licensed, and in
alpha approaching GA — try it, and tell us what breaks. In the next
video we'll connect ARGO to a Telegram bot. Thanks for watching."
