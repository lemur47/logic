#!/usr/bin/env python3
"""Smoke-test an MCP stdio server by making it *answer*, not merely start.

Why this exists
---------------
A server whose imports fail exits silently, and every MCP client reports that as
nothing more than "connection closed". So "the process did not immediately exit"
is not evidence that a build works. This drives a real `initialize` handshake and
a `tools/list` call, and fails loudly if either does not come back.

It caught nothing at the time it was written — it exists because its *absence*
let 0.1.1 ship with an unbounded `mcp` requirement. When `mcp` 2.0.0 removed
FastMCP, every fresh install of the published wheel died at import while CI stayed
green, because `uv.lock` pinned a working version. A lockfile proves the
repository works; only an unlocked resolve of the built artefact proves the
release works.

Usage
-----
    python scripts/mcp_smoke.py [--expect-tools N] -- <command> [args...]

    python scripts/mcp_smoke.py -- pmorun-mcp
    python scripts/mcp_smoke.py --expect-tools 4 -- uvx --refresh pmorun-mcp

Exit status is 0 only if the server completed the handshake and listed tools.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

# Generous, because a cold `uvx` run resolves and downloads from PyPI first.
TIMEOUT_SECONDS = 300


def _send(proc: subprocess.Popen[str], message: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def _read_response(proc: subprocess.Popen[str], want_id: int) -> dict | None:
    """Read stdout until the response carrying ``want_id`` arrives.

    Skips notifications and log frames, which are interleaved with responses on
    the same stream and are not errors.
    """
    assert proc.stdout is not None
    while True:
        line = proc.stdout.readline()
        if not line:  # stream closed — the server died
            return None
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("id") == want_id:
            return message


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect-tools",
        type=int,
        default=None,
        help="Fail unless exactly this many tools are registered.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Server command, after --")
    args = parser.parse_args()

    command = [arg for arg in args.command if arg != "--"]
    if not command:
        print("smoke: no server command given", file=sys.stderr)
        return 2

    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,  # let the server's own diagnostics reach the log
        text=True,
        bufsize=1,
    )

    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mcp-smoke", "version": "1"},
                },
            },
        )
        initialised = _read_response(proc, 1)
        if not initialised or "result" not in initialised:
            print(
                "smoke: FAIL — no initialize result. The server exited without "
                "answering, which is what a failed import looks like.",
                file=sys.stderr,
            )
            return 1
        print(f"smoke: initialize OK — serverInfo={initialised['result'].get('serverInfo')}")

        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        listed = _read_response(proc, 2)
        if not listed or "result" not in listed:
            print("smoke: FAIL — no tools/list result.", file=sys.stderr)
            return 1

        names = sorted(tool["name"] for tool in listed["result"].get("tools", []))
        print(f"smoke: tools/list OK — {len(names)} tools: {', '.join(names)}")

        if args.expect_tools is not None and len(names) != args.expect_tools:
            print(
                f"smoke: FAIL — expected exactly {args.expect_tools} tools, got {len(names)}.",
                file=sys.stderr,
            )
            return 1
    finally:
        if proc.stdin is not None:
            proc.stdin.close()
        try:
            proc.wait(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("smoke: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
