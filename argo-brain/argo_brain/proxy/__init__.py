"""OpenAI-compatible proxy package — spec section 4.9.

Exposes an OpenAI-shaped HTTP API (`/v1/chat/completions`, `/v1/models`)
that forwards requests to an `AgentCore`. This lets existing OpenAI client
libraries talk to the ARGO brain without modification.

Public surface:
  * `OpenAIProxy`                — the stdlib `http.server` proxy class
  * `openai_request_to_message`  — pure converter: OpenAI request -> message
  * `agent_response_to_openai`   — pure converter: agent text -> OpenAI envelope
"""

from __future__ import annotations

from argo_brain.proxy.server import (
    OpenAIProxy,
    agent_response_to_openai,
    openai_request_to_message,
)

__all__ = [
    "OpenAIProxy",
    "openai_request_to_message",
    "agent_response_to_openai",
]
