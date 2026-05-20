# Channels

Channels are the messaging-platform adapters that connect ARGO to the outside
world. Every channel implements the same `Channel` contract
(`argo_brain/channels/base.py`), so they all bridge to the agent the same way.

## Supported channels

The brain ships the following channel adapters:

| Channel | Module | Connection model |
|---|---|---|
| Telegram | `telegram.py` | Long polling. |
| Slack | `webhook.py` (`SlackChannel`) | Slack Events API (inbound webhook). |
| Email | `email_channel.py` | IMAP for receiving, SMTP for sending. |
| IRC | `irc.py` | A raw TCP connection. |
| Matrix | `matrix.py` | Matrix client/server API. |
| Mattermost | `mattermost.py` | Mattermost API. |
| Rocket.Chat | `rocketchat.py` | Rocket.Chat API. |
| Generic webhook | `webhook.py` (`GenericWebhookChannel`) | Inbound HTTP webhook. |

Additional adapter modules are present for Viber, WhatsApp and LINE; the
remaining platforms follow the same `Channel` contract and are filled in
across later sprints.

## How channels are bridged to the agent

A **polling** channel (such as Telegram) is connected to the agent with the
`run_channel()` runner: it polls the platform for new messages, forwards each
to `AgentCore`, and sends the agent's reply back.

A **webhook** channel does not poll. Instead, the HTTP gateway exposes a
`/webhook/<platform>` route — inbound HTTP requests on that route are handed
to the matching channel. The webhook map is built when you run
`python3 -m argo_brain serve`: the generic webhook is always registered, and
Slack is added automatically when `SLACK_BOT_TOKEN` is set.

## Connecting Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Export the token and run the channel:

   ```bash
   export TELEGRAM_BOT_TOKEN=<your-token>
   python3 -m argo_brain telegram
   ```

The `telegram` command exits with instructions if the token is missing.

## Connecting Slack

1. Create a Slack app and obtain a bot token.
2. Export the token and start the HTTP gateway:

   ```bash
   export SLACK_BOT_TOKEN=<your-bot-token>
   python3 -m argo_brain serve --port 8000
   ```

3. Point your Slack app's Events API request URL at the gateway's
   `/webhook/slack` route. The gateway prints the registered webhook
   platforms on startup.

## Connecting a generic webhook

The generic webhook is always available when the HTTP gateway is running.
Post messages to `/webhook/generic`:

```bash
curl -s http://127.0.0.1:8000/webhook/generic \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "alice", "message": "Hello from a webhook!"}'
```

This is the simplest way to integrate a platform that ARGO does not yet have
a dedicated adapter for.

## Connecting Email, IRC, Matrix, Mattermost and Rocket.Chat

These adapters use platform-specific credentials (IMAP/SMTP servers for
Email, server host and credentials for IRC/Matrix/Mattermost/Rocket.Chat).
They implement the same `Channel` interface and are bridged to the agent with
the `run_channel()` runner. Provide the relevant credentials via the
environment or configuration and connect the adapter the same way the
Telegram channel is connected.

## See also

- [CLI reference](cli.md) — the `telegram` and `serve` commands.
- [Configuration](configuration.md) — channel credentials.
</content>
