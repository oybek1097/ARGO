"""ARGO brain CLI — `python -m argo_brain <command>`.

Commands:
  chat      Interactive conversation (Mock provider, no API key needed)
  serve     Run the HTTP API gateway
  ipc       Run the IPC server (Unix socket)
  selftest  Self-check (smoke test)
  version   Version information
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from argo_brain import __version__
from argo_brain.config import Settings, load_settings


def _build_agent(settings: Settings):
    """Builds an AgentCore with skills discovered from the data directory."""
    from argo_brain.core import AgentCore
    from argo_brain.skills import SkillLoader

    skills_dir = settings.resolved_data_dir.parent / "skills"
    loader = SkillLoader(skills_dir)
    loader.load()
    return AgentCore(settings, skills=loader)


async def _cmd_chat() -> int:
    from argo_brain.core import AgentRequest

    settings = load_settings()
    settings.ensure_dirs()
    agent = _build_agent(settings)
    print(f"ARGO brain v{__version__} — interaktiv chat (chiqish: /exit)")
    print(f"Provayder: {agent.provider.model}\n")
    try:
        while True:
            try:
                line = input("siz> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line in ("/exit", "/quit", "/q"):
                break
            resp = await agent.process(AgentRequest(user_id="cli-user", message=line))
            tag = f" [{', '.join(resp.tools_used)}]" if resp.tools_used else ""
            print(f"argo> {resp.content}")
            print(
                f"      ({resp.language} · {resp.model} · {resp.iterations} iter · "
                f"{resp.duration_ms}ms{tag})\n"
            )
    finally:
        agent.close()
    return 0


async def _cmd_ipc() -> int:
    from argo_brain.ipc import IPCServer

    settings = load_settings()
    settings.ensure_dirs()
    server = IPCServer(settings, agent=_build_agent(settings))
    print(f"ARGO brain v{__version__} — IPC server")
    print(f"Socket: {settings.resolved_ipc_socket}  (to'xtatish: Ctrl+C)")
    try:
        await server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()
    return 0


def _build_webhooks() -> dict:
    """Builds the webhook channel map from the environment."""
    import os

    from argo_brain.channels import GenericWebhookChannel, SlackChannel

    hooks: dict = {"generic": GenericWebhookChannel()}
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if slack_token:
        hooks["slack"] = SlackChannel(slack_token)
    return hooks


def _cmd_serve(host: str, port: int) -> int:
    from argo_brain.api import HTTPGateway

    settings = load_settings()
    settings.ensure_dirs()
    webhooks = _build_webhooks()
    gateway = HTTPGateway(
        settings, host=host, port=port,
        agent=_build_agent(settings), webhooks=webhooks,
    )
    print(f"ARGO brain v{__version__} — HTTP gateway")
    print(f"Manzil: http://{host}:{port}  (to'xtatish: Ctrl+C)")
    print(f"Webhook platformalar: {', '.join(webhooks)}")
    try:
        gateway.serve_forever()
    except KeyboardInterrupt:
        gateway.stop()
    return 0


async def _cmd_telegram() -> int:
    """Runs the Telegram channel, bridging it to the agent."""
    import os

    from argo_brain.channels import TelegramChannel, run_channel

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("Xato: TELEGRAM_BOT_TOKEN muhit oʻzgaruvchisi oʻrnatilmagan.")
        print("Telegram'da @BotFather orqali bot yarating, soʻngra:")
        print("  export TELEGRAM_BOT_TOKEN=<token>")
        return 1

    settings = load_settings()
    settings.ensure_dirs()
    agent = _build_agent(settings)
    print(f"ARGO brain v{__version__} — Telegram kanali")
    print(f"Provayder: {agent.provider.model}  (to'xtatish: Ctrl+C)")
    try:
        await run_channel(TelegramChannel(token), agent)
    except KeyboardInterrupt:
        pass
    finally:
        agent.close()
    return 0


def _cmd_setup() -> int:
    """Interactive first-run setup wizard (Hermes-style)."""
    import json
    import os
    from pathlib import Path

    home = Path(os.environ.get("ARGO_HOME", Path.home() / ".argo"))
    print(f"ARGO Agent v{__version__} — sozlash sehrgari\n")

    def ask(prompt: str, default: str) -> str:
        try:
            answer = input(f"{prompt} [{default}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        return answer or default

    print("LLM modelni tanlang:")
    print("  1) mock              — API kalitsiz (sinov uchun)")
    print("  2) claude-sonnet-4-6 — Anthropic (kalit kerak)")
    print("  3) claude-opus-4-7   — Anthropic (kalit kerak)")
    choice = ask("Tanlov", "1")
    model = {"1": "mock", "2": "claude-sonnet-4-6", "3": "claude-opus-4-7"}.get(
        choice, choice
    )

    api_key = ""
    if model != "mock":
        api_key = ask("ANTHROPIC_API_KEY", "")

    port = ask("HTTP gateway porti", "8000")

    # Create the standard directory layout.
    home.mkdir(parents=True, exist_ok=True)
    (home / "data").mkdir(exist_ok=True)
    (home / "skills").mkdir(exist_ok=True)

    config = {"model": model, "log_level": "INFO"}
    (home / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if api_key:
        env_file = home / "env"
        env_file.write_text(
            f"export ANTHROPIC_API_KEY={api_key}\nexport ARGO_CORE_PORT={port}\n",
            encoding="utf-8",
        )
        env_file.chmod(0o600)

    print(f"\nTayyor. Konfiguratsiya: {home / 'config.json'}")
    print("Keyingi qadamlar:")
    if api_key:
        print(f"  source {home / 'env'}")
    print("  python3 -m argo_brain ipc      # brain (IPC)")
    print("  python3 -m argo_brain serve    # HTTP gateway")
    print("  python3 -m argo_brain doctor   # tekshiruv")
    return 0


def _cmd_doctor() -> int:
    """Diagnoses the installation — spec section 4.2 (`argo doctor`)."""
    import os
    import sys as _sys
    from pathlib import Path

    print(f"ARGO Agent v{__version__} — doctor\n")
    home = Path(os.environ.get("ARGO_HOME", Path.home() / ".argo"))
    checks: list[tuple[str, bool, str]] = []

    py_ok = _sys.version_info >= (3, 11)
    checks.append(("Python >= 3.11", py_ok, _sys.version.split()[0]))

    cfg = home / "config.json"
    checks.append(("Konfiguratsiya fayli", cfg.is_file(), str(cfg)))

    checks.append(
        ("Ma'lumotlar katalogi", (home / "data").is_dir(), str(home / "data"))
    )

    key_set = bool(os.environ.get("ANTHROPIC_API_KEY"))
    checks.append(("ANTHROPIC_API_KEY", key_set, "o'rnatilgan" if key_set else "yo'q (mock rejim)"))

    core = Path(__file__).resolve().parents[2] / "argo-core" / "target" / "release" / "argo-core"
    checks.append(("argo-core binary", core.is_file(), str(core)))

    try:
        import argo_brain.core  # noqa: F401
        brain_ok = True
    except Exception:  # noqa: BLE001
        brain_ok = False
    checks.append(("argo-brain importi", brain_ok, "argo_brain.core"))

    for name, ok, detail in checks:
        print(f"  {'OK  ' if ok else 'XATO'}  {name:24s} {detail}")
    # The API key being unset is acceptable (mock mode), so it is not fatal.
    fatal = [c for c in checks if not c[1] and c[0] != "ANTHROPIC_API_KEY"
             and c[0] != "argo-core binary"]
    print(f"\n{'Tizim sogʻlom.' if not fatal else 'Muammolar topildi.'}")
    return 0 if not fatal else 1


async def _cmd_selftest() -> int:
    """Smoke test that exercises the main subsystems."""
    import tempfile
    from pathlib import Path

    from argo_brain.core import AgentCore, AgentRequest
    from argo_brain.cron import parse_schedule
    from argo_brain.multi_agent import KanbanManager

    print(f"ARGO brain v{__version__} — selftest\n")
    checks: list[tuple[str, bool]] = []

    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(data_dir=tmp, db_path=str(Path(tmp) / "t.db"))
        agent = AgentCore(settings)
        try:
            r1 = await agent.process(
                AgentRequest(user_id="u1", message="Salom, qalaysan?")
            )
            checks.append(("oddiy chat", bool(r1.content) and r1.language == "uz"))

            r2 = await agent.process(
                AgentRequest(user_id="u1", message="hisobla 2 + 3 * 4")
            )
            checks.append(("calculate tool", "14" in r2.content))

            r3 = await agent.process(
                AgentRequest(user_id="u1", message="hozir soat nechi?")
            )
            checks.append(("current_time tool", "current_time" in r3.tools_used))

            hist = await agent.memory.history("u1")
            checks.append(("xotira saqlandi", len(hist) >= 6))

            checks.append(
                ("tool suite", len(agent.registry.names()) >= 10)
            )
        finally:
            agent.close()

        # Kanban lifecycle
        km = KanbanManager(Path(tmp) / "kan.db")
        board = km.create_board("u1", "test board")
        km.add_task(board, "task A", "do A")
        claimed = km.claim_task(board, "agent-1")
        if claimed:
            km.complete_task(claimed["id"], "done")
        checks.append(("kanban lifecycle", km.board_status(board).get("done") == 1))
        km.close()

    # Cron natural-language parsing
    checks.append(
        ("cron parser", parse_schedule("every 5 minutes") == {"interval": 300})
    )

    for name, ok in checks:
        print(f"  {'OK  ' if ok else 'XATO'}  {name}")
    passed = all(ok for _, ok in checks)
    summary = "Hammasi muvaffaqiyatli." if passed else "Ba'zi tekshiruvlar muvaffaqiyatsiz."
    print(f"\n{summary}")
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="argo-brain", description="ARGO Agent v3.0 — Python brain"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("setup", help="interactive first-run setup wizard")
    sub.add_parser("doctor", help="diagnose the installation")
    sub.add_parser("chat", help="interactive conversation")
    serve_p = sub.add_parser("serve", help="run the HTTP API gateway")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)
    sub.add_parser("ipc", help="run the IPC server")
    sub.add_parser("telegram", help="run the Telegram channel")
    sub.add_parser("selftest", help="self-check")
    sub.add_parser("version", help="version information")

    args = parser.parse_args(argv)
    cmd = args.command or "chat"

    if cmd == "version":
        print(f"argo-brain {__version__}")
        return 0
    if cmd == "setup":
        return _cmd_setup()
    if cmd == "doctor":
        return _cmd_doctor()
    if cmd == "chat":
        return asyncio.run(_cmd_chat())
    if cmd == "ipc":
        return asyncio.run(_cmd_ipc())
    if cmd == "telegram":
        return asyncio.run(_cmd_telegram())
    if cmd == "serve":
        return _cmd_serve(args.host, args.port)
    if cmd == "selftest":
        return asyncio.run(_cmd_selftest())

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
