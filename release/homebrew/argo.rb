# ARGO Agent v3.0 — Homebrew formula.
#
# This formula is intended to be served from a future dedicated tap,
# `argo-agent/homebrew-argo`, so that users can install ARGO with:
#
#     brew tap argo-agent/argo
#     brew install argo
#
# Until that tap is published, the formula can be installed directly:
#
#     brew install --build-from-source ./release/homebrew/argo.rb
#
# ARGO has two components, both installed by this formula:
#   * argo-core  — the Rust HTTP gateway (compiled with cargo at install time).
#   * argo-brain — the Python 3.12 brain (stdlib-only; no pip install needed).
#
# Status: alpha approaching the v3.0.0 GA. Pin the `url`/`sha256` below to a
# real release tarball before publishing the formula to the tap.
class Argo < Formula
  desc "Open-source multilingual AI agent platform (Rust gateway + Python brain)"
  homepage "https://github.com/argo-agent/argo"
  url "https://github.com/argo-agent/argo/archive/refs/tags/v3.0.0.tar.gz"
  # Replace with the real tarball checksum when the v3.0.0 release is cut.
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"
  head "https://github.com/argo-agent/argo.git", branch: "main"

  # Build-time toolchains.
  depends_on "rust" => :build

  # Runtime: the Python brain targets the stdlib of Python 3.12.
  depends_on "python@3.12"

  def install
    # 1. Build argo-core (the Rust gateway). The release profile in
    #    argo-core/Cargo.toml produces a small, stripped binary.
    cd "argo-core" do
      system "cargo", "build", "--release", "--locked"
      libexec.install "target/release/argo-core"
    end

    # 2. Install the stdlib-only argo-brain package under libexec so it is
    #    importable without touching Homebrew's site-packages.
    (libexec/"argo-brain").install Dir["argo-brain/argo_brain"]

    # 3. Generate an `argo` wrapper that dispatches between the two
    #    components. `argo core ...` runs the Rust gateway; anything else
    #    is forwarded to `python3 -m argo_brain`.
    python = Formula["python@3.12"].opt_bin/"python3.12"
    (bin/"argo").write <<~SH
      #!/bin/bash
      # ARGO Agent launcher (installed by Homebrew).
      set -euo pipefail
      ARGO_CORE="#{libexec}/argo-core"
      ARGO_BRAIN="#{libexec}/argo-brain"

      if [ "${1:-}" = "core" ]; then
        shift
        exec "$ARGO_CORE" "$@"
      fi

      export PYTHONPATH="$ARGO_BRAIN${PYTHONPATH:+:$PYTHONPATH}"
      exec "#{python}" -m argo_brain "$@"
    SH
    chmod 0755, bin/"argo"
  end

  def caveats
    <<~EOS
      ARGO installed two components:
        * argo-core  — Rust gateway   (run: `argo core`)
        * argo-brain — Python brain   (run: `argo chat`, `argo serve`, ...)

      Get started with the interactive setup wizard:
        argo setup

      Data and configuration are stored under ~/.argo by default
      (override with the ARGO_HOME environment variable).
    EOS
  end

  test do
    # The brain exposes a `version` subcommand that prints "argo-brain <ver>".
    assert_match "argo-brain", shell_output("#{bin}/argo version")

    # The core binary should also be runnable via `argo core`.
    assert_predicate libexec/"argo-core", :executable?
  end
end
