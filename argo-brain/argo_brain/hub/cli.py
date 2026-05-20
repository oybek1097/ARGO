"""Hub command-line interface — spec section 4.7 / Sprint 11.

Drives the skill & plugin marketplace from the terminal. Reachable both as
``python3 -m argo_brain.hub`` and, wired through the brain CLI, as
``argo hub <command>``:

    argo hub search kubernetes
    argo hub info deploy-k8s
    argo hub install deploy-k8s
    argo hub publish ./my-skill.md --name my-skill --publisher me --key SECRET
    argo hub trust add argo-team <key>
    argo hub serve --port 8730

By default the CLI works against the local registry at ``~/.argo/hub``;
``--hub <url>`` points any read/write command at a remote `HubServer`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from argo_brain.hub.client import HubClient, HubError
from argo_brain.hub.package import ArgoPackage, PackageError, build_skill_package
from argo_brain.hub.registry import HubRegistry, RegistryError
from argo_brain.hub.remote import RemoteRegistry
from argo_brain.hub.signing import TrustStore
from argo_brain.skills.loader import _parse_frontmatter

_DEFAULT_REGISTRY = Path("~/.argo/hub").expanduser()
_DEFAULT_TRUST = Path("~/.argo/trust.json").expanduser()
_DEFAULT_SKILLS = Path("~/.argo/skills").expanduser()
_DEFAULT_PLUGINS = Path("~/.argo/plugins").expanduser()


def _registry(args: argparse.Namespace):
    """Resolve the registry: a remote hub if ``--hub`` is set, else local."""
    if getattr(args, "hub", None):
        return RemoteRegistry(args.hub)
    return HubRegistry(args.registry)


def _client(args: argparse.Namespace) -> HubClient:
    trust = TrustStore.from_file(args.trust)
    return HubClient(
        _registry(args),
        trust=trust,
        skills_dir=_DEFAULT_SKILLS,
        plugins_dir=_DEFAULT_PLUGINS,
    )


def _load_trust(path: Path) -> dict[str, str]:
    p = Path(path).expanduser()
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _save_trust(path: Path, keys: dict[str, str]) -> None:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(keys, indent=2), encoding="utf-8")


# -- command handlers ------------------------------------------------------
def _cmd_search(args: argparse.Namespace) -> int:
    hits = _registry(args).search(args.query or "", kind=args.kind)
    if not hits:
        print("No packages found.")
        return 0
    print(f"{'name':<28} {'version':<10} {'kind':<8} description")
    print("-" * 78)
    for e in hits:
        print(f"{e.name:<28} {e.version:<10} {e.kind:<8} {e.description[:34]}")
    print(f"\n{len(hits)} package(s).")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    entry = _registry(args).get(args.name, args.version)
    print(json.dumps(entry.to_dict(), indent=2, ensure_ascii=False))
    return 0


def _cmd_versions(args: argparse.Namespace) -> int:
    rows = _registry(args).versions(args.name)
    if not rows:
        print(f"No such package: {args.name}")
        return 1
    for e in rows:
        print(f"{e.version:<12} {e.published_at}  ({e.downloads} downloads)")
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    client = _client(args)
    result = client.install(
        args.name, version=args.version, require_signature=not args.no_verify
    )
    verified = "verified" if result.signature_verified else "UNVERIFIED"
    print(f"Installed {result.entry.ref} ({verified})")
    for path in result.paths:
        print(f"  {path}")
    return 0


def _cmd_publish(args: argparse.Namespace) -> int:
    source = Path(args.file).expanduser()
    if not source.is_file():
        print(f"No such file: {source}")
        return 1
    if source.suffix == ".argopkg":
        package = ArgoPackage.from_bytes(source.read_bytes())
    elif source.suffix == ".md":
        if not args.name:
            print("--name is required when publishing a .md skill")
            return 1
        raw = source.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(raw)
        triggers = [t.strip() for t in meta.get("trigger", "").split(",") if t.strip()]
        package = build_skill_package(
            name=args.name,
            version=args.version or "1.0.0",
            markdown=raw,
            author=args.publisher,
            description=meta.get("description", ""),
            category=meta.get("category", "general"),
            triggers=triggers,
        )
    else:
        print("Unsupported file type — expected a .md skill or a .argopkg")
        return 1
    client = _client(args)
    entry = client.publish(package, publisher=args.publisher, key=args.key)
    print(f"Published {entry.ref} as {args.publisher}")
    return 0


def _cmd_trust(args: argparse.Namespace) -> int:
    keys = _load_trust(args.trust)
    if args.trust_action == "add":
        keys[args.publisher] = args.key
        _save_trust(args.trust, keys)
        print(f"Trusted publisher: {args.publisher}")
    elif args.trust_action == "remove":
        keys.pop(args.publisher, None)
        _save_trust(args.trust, keys)
        print(f"Removed publisher: {args.publisher}")
    else:  # list
        if not keys:
            print("No trusted publishers.")
        for publisher in sorted(keys):
            print(publisher)
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from argo_brain.hub.server import HubServer

    server = HubServer(HubRegistry(args.registry), host=args.host, port=args.port)
    print(f"argo-hub serving {args.registry} on {server.url}/hub/v1")
    print("Press Ctrl+C to stop.")
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print("\nStopped.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="argo hub", description="ARGO skill & plugin marketplace"
    )
    parser.add_argument(
        "--registry", type=Path, default=_DEFAULT_REGISTRY,
        help=f"local registry directory (default: {_DEFAULT_REGISTRY})",
    )
    parser.add_argument(
        "--hub", default=None,
        help="remote hub base URL; overrides --registry for read/write commands",
    )
    parser.add_argument(
        "--trust", type=Path, default=_DEFAULT_TRUST,
        help=f"trusted-publisher key file (default: {_DEFAULT_TRUST})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="search the catalogue")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--kind", choices=["skill", "plugin"], default=None)
    p.set_defaults(func=_cmd_search)

    p = sub.add_parser("info", help="show one package's metadata")
    p.add_argument("name")
    p.add_argument("--version", default=None)
    p.set_defaults(func=_cmd_info)

    p = sub.add_parser("versions", help="list a package's published versions")
    p.add_argument("name")
    p.set_defaults(func=_cmd_versions)

    p = sub.add_parser("install", help="install a package locally")
    p.add_argument("name")
    p.add_argument("--version", default=None)
    p.add_argument("--no-verify", action="store_true",
                   help="install even if the signature cannot be verified")
    p.set_defaults(func=_cmd_install)

    p = sub.add_parser("publish", help="publish a skill or plugin")
    p.add_argument("file", help="a .md skill or a .argopkg package")
    p.add_argument("--name", default=None, help="package name (required for .md)")
    p.add_argument("--version", default=None, help="package version (default 1.0.0)")
    p.add_argument("--publisher", required=True)
    p.add_argument("--key", required=True, help="the publisher's signing key")
    p.set_defaults(func=_cmd_publish)

    p = sub.add_parser("trust", help="manage trusted publishers")
    p.add_argument("trust_action", choices=["add", "remove", "list"])
    p.add_argument("publisher", nargs="?", default=None)
    p.add_argument("key", nargs="?", default=None)
    p.set_defaults(func=_cmd_trust)

    p = sub.add_parser("serve", help="serve the local registry over HTTP")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8730)
    p.set_defaults(func=_cmd_serve)

    return parser


def run(argv: list[str] | None = None) -> int:
    """Entry point for ``python3 -m argo_brain.hub`` and ``argo hub``."""
    args = _build_parser().parse_args(argv)
    if args.command == "trust" and args.trust_action == "add" and (
        not args.publisher or not args.key
    ):
        print("usage: argo hub trust add <publisher> <key>")
        return 1
    try:
        return args.func(args)
    except (RegistryError, PackageError, HubError) as exc:
        print(f"error: {exc}")
        return 1
