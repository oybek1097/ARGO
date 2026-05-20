"""``python3 -m argo_brain.hub`` — the hub & marketplace CLI entry point."""

import sys

from argo_brain.hub.cli import run

if __name__ == "__main__":
    sys.exit(run())
