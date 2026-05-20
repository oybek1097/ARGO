"""Web dashboard for the ARGO HTTP gateway.

This module provides a single self-contained HTML page (inline CSS and
vanilla JavaScript, no external dependencies) that acts as a minimal chat
dashboard for the ARGO agent. It talks to the existing gateway endpoints:

  GET  /api/health  -> used to display the running argo version
  POST /api/chat    -> used to send user messages and render replies

To serve it, the existing `argo_brain.api.server.HTTPGateway` only needs a
single extra route in its `do_GET` handler (see this module's docstring at
the project level / task report). This file does NOT modify the server.
"""

from __future__ import annotations

# The complete dashboard page. Kept as a module-level constant so it can be
# imported cheaply and asserted against in tests without rendering overhead.
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARGO Dashboard</title>
<style>
  /* Dark theme, clean and minimal. */
  * { box-sizing: border-box; }
  html, body {
    margin: 0;
    height: 100%;
    font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
    background: #0e1116;
    color: #e6e6e6;
  }
  body { display: flex; flex-direction: column; }
  header {
    padding: 14px 20px;
    background: #161b22;
    border-bottom: 1px solid #2a313c;
    display: flex;
    align-items: baseline;
    gap: 12px;
  }
  header h1 { font-size: 18px; margin: 0; color: #58a6ff; }
  header .version { font-size: 12px; color: #8b949e; }
  #messages {
    flex: 1;
    overflow-y: auto;
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .msg {
    max-width: 70%;
    padding: 9px 13px;
    border-radius: 10px;
    line-height: 1.4;
    white-space: pre-wrap;
    word-wrap: break-word;
  }
  .msg.user { align-self: flex-end; background: #1f6feb; color: #fff; }
  .msg.argo { align-self: flex-start; background: #21262d; color: #e6e6e6; }
  .msg.error { align-self: flex-start; background: #5c1f1f; color: #ffd7d7; }
  footer {
    display: flex;
    gap: 8px;
    padding: 14px 20px;
    background: #161b22;
    border-top: 1px solid #2a313c;
  }
  #input {
    flex: 1;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid #2a313c;
    background: #0e1116;
    color: #e6e6e6;
    font-size: 14px;
  }
  #input:focus { outline: none; border-color: #58a6ff; }
  #send {
    padding: 10px 18px;
    border: none;
    border-radius: 8px;
    background: #238636;
    color: #fff;
    font-size: 14px;
    cursor: pointer;
  }
  #send:disabled { background: #2a313c; cursor: not-allowed; }
</style>
</head>
<body>
<header>
  <h1>ARGO Dashboard</h1>
  <span class="version" id="version">version: loading...</span>
</header>
<div id="messages"></div>
<footer>
  <input id="input" type="text" placeholder="Type a message and press Enter..."
         autocomplete="off">
  <button id="send">Send</button>
</footer>
<script>
  // Vanilla JS only -- no external libraries or CDN.
  var messages = document.getElementById("messages");
  var input = document.getElementById("input");
  var sendBtn = document.getElementById("send");

  // Append a chat bubble of the given role ("user", "argo" or "error").
  function appendMessage(role, text) {
    var div = document.createElement("div");
    div.className = "msg " + role;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  // Load the argo version from the health endpoint.
  function loadVersion() {
    fetch("/api/health")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        document.getElementById("version").textContent =
          "version: " + (data.version || "unknown");
      })
      .catch(function () {
        document.getElementById("version").textContent = "version: unavailable";
      });
  }

  // Send the current input value to /api/chat and render the reply.
  function sendMessage() {
    var text = input.value.trim();
    if (!text) { return; }
    appendMessage("user", text);
    input.value = "";
    sendBtn.disabled = true;
    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "web-user", message: text })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var reply = data.content || data.message || data.error || "(no reply)";
        appendMessage(data.error ? "error" : "argo", reply);
      })
      .catch(function (err) {
        appendMessage("error", "Request failed: " + err);
      })
      .finally(function () {
        sendBtn.disabled = false;
        input.focus();
      });
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { sendMessage(); }
  });

  loadVersion();
  input.focus();
</script>
</body>
</html>
"""


def dashboard_page() -> str:
    """Returns the complete self-contained dashboard HTML page."""
    return DASHBOARD_HTML
