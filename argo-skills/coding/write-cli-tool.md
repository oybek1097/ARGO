---
name: Build a Command-Line Tool
slug: write-cli-tool
trigger: cli, command line tool, argparse, terminal app
category: coding
quality: 0.73
author: argo-team
license: MIT
requires_tools: [file_write]
---

# Build a Command-Line Tool

1. Define subcommands, flags, and positional arguments up front.
2. Parse arguments with a standard library parser; validate early.
3. Read from stdin and write results to stdout; send errors to stderr.
4. Return meaningful exit codes (0 success, non-zero on failure).
5. Add `--help` text and a `--version` flag.
