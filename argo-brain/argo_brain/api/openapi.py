"""OpenAPI 3.1 specification generator for the HTTP gateway — spec section 6.

This module produces a machine-readable description of the public HTTP
surface served by `argo_brain.api.server.HTTPGateway`. The spec is built
purely from Python dicts (stdlib only) so it can be served as JSON at
`GET /openapi.json` or consumed by external tooling (Swagger UI, codegen).

The described endpoints mirror the gateway exactly:

  GET  /api/health         -> liveness probe + version
  GET  /api/version        -> version info
  POST /api/chat           -> {"user_id", "message", ...} -> AgentResponse
  GET  /api/history        -> message history for a user
  POST /webhook/{platform} -> inbound webhook for a registered channel
"""

from __future__ import annotations

import json

from argo_brain import __version__

# OpenAPI version implemented by this generator (spec section 6).
OPENAPI_VERSION = "3.1.0"


def _components() -> dict:
    """Builds the `components/schemas` section.

    These schemas describe the chat request/response shapes (matching
    `AgentRequest` and `AgentResponse.to_dict()`) plus a few small shared
    shapes referenced via `$ref` from the `paths` section.
    """
    return {
        "schemas": {
            # Request body for POST /api/chat (mirrors AgentRequest).
            "ChatRequest": {
                "type": "object",
                "required": ["message"],
                "properties": {
                    "user_id": {
                        "type": "string",
                        "default": "anon",
                        "description": "Identifier of the requesting user.",
                    },
                    "message": {
                        "type": "string",
                        "description": "The user's input message.",
                    },
                    "language": {
                        "type": "string",
                        "default": "",
                        "description": "Language hint; empty means auto-detect.",
                    },
                    "channel": {
                        "type": "string",
                        "default": "http",
                        "description": "Originating channel name.",
                    },
                },
            },
            # Response body for POST /api/chat (mirrors AgentResponse.to_dict()).
            "ChatResponse": {
                "type": "object",
                "required": [
                    "content",
                    "language",
                    "model",
                    "tools_used",
                    "iterations",
                    "duration_ms",
                ],
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The agent's reply text.",
                    },
                    "language": {
                        "type": "string",
                        "description": "Language the reply was produced in.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model that generated the reply.",
                    },
                    "tools_used": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of tools invoked during processing.",
                    },
                    "iterations": {
                        "type": "integer",
                        "description": "Number of agent reasoning iterations.",
                    },
                    "duration_ms": {
                        "type": "integer",
                        "description": "Total processing time in milliseconds.",
                    },
                    "error": {
                        "type": ["string", "null"],
                        "description": "Error message, or null on success.",
                    },
                },
            },
            # GET /api/health payload.
            "HealthResponse": {
                "type": "object",
                "required": ["status", "version"],
                "properties": {
                    "status": {"type": "string", "example": "ok"},
                    "version": {"type": "string"},
                },
            },
            # GET /api/version payload.
            "VersionResponse": {
                "type": "object",
                "required": ["version", "component"],
                "properties": {
                    "version": {"type": "string"},
                    "component": {"type": "string", "example": "argo-brain"},
                },
            },
            # GET /api/history payload.
            "HistoryResponse": {
                "type": "object",
                "required": ["history"],
                "properties": {
                    "history": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Stored message history for the user.",
                    },
                },
            },
            # Generic error envelope returned on 400/404.
            "ErrorResponse": {
                "type": "object",
                "required": ["error"],
                "properties": {
                    "error": {"type": "string"},
                },
            },
            # Generic webhook acknowledgement.
            "WebhookAck": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "skipped": {"type": "boolean"},
                },
            },
        }
    }


def _json_response(ref: str, description: str) -> dict:
    """Helper: builds a JSON response object referencing a component schema."""
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{ref}"},
            }
        },
    }


def _paths() -> dict:
    """Builds the `paths` section describing every gateway endpoint."""
    error_400 = _json_response("ErrorResponse", "Invalid request body.")
    error_404 = _json_response("ErrorResponse", "Resource not found.")
    return {
        "/api/health": {
            "get": {
                "summary": "Liveness probe.",
                "description": "Returns service status and version.",
                "operationId": "getHealth",
                "responses": {
                    "200": _json_response("HealthResponse", "Service is healthy."),
                },
            }
        },
        "/api/version": {
            "get": {
                "summary": "Version information.",
                "operationId": "getVersion",
                "responses": {
                    "200": _json_response("VersionResponse", "Version details."),
                },
            }
        },
        "/api/chat": {
            "post": {
                "summary": "Send a message to the agent.",
                "description": "Processes a chat message and returns the agent's reply.",
                "operationId": "postChat",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ChatRequest"},
                        }
                    },
                },
                "responses": {
                    "200": _json_response("ChatResponse", "The agent's response."),
                    "400": error_400,
                },
            }
        },
        "/api/history": {
            "get": {
                "summary": "Retrieve message history.",
                "operationId": "getHistory",
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "query",
                        "required": False,
                        "description": "User whose history to fetch (default 'anon').",
                        "schema": {"type": "string", "default": "anon"},
                    }
                ],
                "responses": {
                    "200": _json_response("HistoryResponse", "Stored history."),
                },
            }
        },
        "/webhook/{platform}": {
            "post": {
                "summary": "Inbound webhook for a registered channel.",
                "description": (
                    "Accepts a platform-specific webhook payload. May return a "
                    "handshake challenge or an acknowledgement."
                ),
                "operationId": "postWebhook",
                "parameters": [
                    {
                        "name": "platform",
                        "in": "path",
                        "required": True,
                        "description": "Registered webhook platform name.",
                        "schema": {"type": "string"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                        }
                    },
                },
                "responses": {
                    "200": _json_response("WebhookAck", "Webhook accepted."),
                    "400": error_400,
                    "404": error_404,
                },
            }
        },
    }


def build_openapi_spec() -> dict:
    """Returns a valid OpenAPI 3.1 specification as a Python dict.

    The returned dict describes the ARGO Agent HTTP gateway endpoints
    (spec section 6) and is safe to serialise directly to JSON.
    """
    return {
        "openapi": OPENAPI_VERSION,
        "info": {
            "title": "ARGO Agent API",
            "version": __version__,
            "description": "HTTP gateway for the ARGO Agent brain.",
        },
        "paths": _paths(),
        "components": _components(),
    }


def openapi_json() -> str:
    """Returns the OpenAPI specification serialised as a JSON string."""
    return json.dumps(build_openapi_spec(), ensure_ascii=False, indent=2)
