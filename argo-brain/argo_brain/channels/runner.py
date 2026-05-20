"""Channel runner — bridges a `Channel` to the `AgentCore`.

For every inbound message it runs the agent loop and sends the reply back.
A failure on one message is logged and skipped so the channel stays alive.
"""

from __future__ import annotations

import logging

from argo_brain.channels.base import Channel
from argo_brain.core import AgentCore, AgentRequest

log = logging.getLogger("argo_brain.channels.runner")


async def run_channel(channel: Channel, agent: AgentCore) -> None:
    """Runs the receive -> process -> send loop until the channel stops."""
    await channel.start()
    log.info("channel runner active: %s", channel.name)
    try:
        async for msg in channel.receive():
            try:
                resp = await agent.process(
                    AgentRequest(
                        user_id=msg.user_id,
                        message=msg.text,
                        channel=channel.name,
                    )
                )
                await channel.send(msg.target, resp.content)
            except Exception:  # noqa: BLE001 — one bad message must not stop the loop
                log.exception("failed to handle message from %s", msg.user_id)
                try:
                    await channel.send(
                        msg.target, "Sorry, an error occurred."
                    )
                except Exception:  # noqa: BLE001
                    log.exception("failed to send error notice")
    finally:
        await channel.stop()
        log.info("channel runner stopped: %s", channel.name)
