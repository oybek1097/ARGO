# Tutorial 03 — Connecting a Telegram bot (English)

**Topic:** Connecting ARGO to a Telegram bot
**Language:** English
**Target duration:** ~4 minutes

---

### Scene 1 — Intro (0:00–0:25)

ON SCREEN: ARGO logo, then a Telegram chat window.

NARRATION: "Welcome back. So far we've talked to ARGO from the terminal.
In this video we'll give ARGO a Telegram bot, so anyone can chat with it
from their phone."

### Scene 2 — Create a bot with BotFather (0:25–1:25)

ON SCREEN: the Telegram app, a chat with @BotFather.

NARRATION: "Telegram bots are created by a bot called BotFather. Open
Telegram, search for BotFather, and start a chat. Send the slash-newbot
command."

ON SCREEN (typed in BotFather):
```
/newbot
```

NARRATION: "BotFather asks for a name and a username for your bot. Pick
anything you like — the username must end in 'bot'. When you're done,
BotFather gives you a token. That token is a secret — treat it like a
password."

### Scene 3 — Set the token (1:25–2:15)

ON SCREEN:
```
export TELEGRAM_BOT_TOKEN=123456:ABC-your-token-here
```

NARRATION: "ARGO reads the bot token from an environment variable called
TELEGRAM_BOT_TOKEN. Set it in your shell, pasting the token BotFather
gave you. For a permanent setup, put it in your environment file rather
than typing it each time."

### Scene 4 — Start the Telegram channel (2:15–3:05)

ON SCREEN:
```
cd argo-brain
python3 -m argo_brain telegram
```

NARRATION: "Now start ARGO's Telegram channel with the telegram
subcommand. ARGO connects to Telegram and begins listening for messages.
Leave this process running — it's what serves your bot."

### Scene 5 — Chat with the bot (3:05–3:40)

ON SCREEN: the Telegram app, opening the new bot and sending a message.

NARRATION: "Open your bot in Telegram and send it a message. ARGO
receives it, runs the same agent loop you saw in the CLI, and replies in
the chat. And because language detection is built in, you can message it
in Uzbek or Russian and it answers in kind."

ON SCREEN (typed in the bot chat):
```
Salom! O'zingni tanishtir.
```

### Scene 6 — Closing / call to action (3:40–4:05)

ON SCREEN: ARGO logo, GitHub URL, "Next: Deploying with Docker Compose".

NARRATION: "That's a working Telegram bot powered by ARGO. Remember:
keep your token secret, and never commit it to a repository. ARGO is
open-source, MIT licensed, and in alpha approaching GA. In the final
video we'll deploy ARGO properly with Docker Compose. Thanks for
watching."
