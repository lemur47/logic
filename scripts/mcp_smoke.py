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
import selectors
import subprocess
import sys

# Generous, because a cold `uvx` run resolves and downloads from PyPI first. This
# bounds the wait for each response: a server that starts but never answers — a
# hung resolve, a blocking network call, something waiting on a prompt — must fail
# this check rather than hang it. Without an explicit bound the read blocks
# forever, and in CI that means burning the job's whole timeout to learn nothing.
TIMEOUT_SECONDS = 300


def _send(proc: subprocess.Popen[str], message: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def _read_response(proc: subprocess.Popen[str], want_id: int, timeout: float) -> dict | None:
    """Read stdout until the response carrying ``want_id`` arrives.

    Skips notifications and log frames, which are interleaved with responses on
    the same stream and are not errors. Returns None if the stream closes (the
    server died) or nothing arrives within ``timeout`` seconds (it hung) — both are
    failures, and the caller reports them as such.
    """
    assert proc.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    try:
        while True:
            # Bound the wait per line. A server that answers slowly still passes;
            # one that never answers fails instead of blocking the run.
            if not selector.select(timeout=timeout):
                print(
                    f"smoke: no response within {timeout}s — the server "
                    "started but is not answering.",
                    file=sys.stderr,
                )
                return None
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
    finally:
        selector.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect-tools",
        type=int,
        default=None,
        help="Fail unless exactly this many tools are registered.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=TIMEOUT_SECONDS,
        help=(
            f"Seconds to wait for each response (default {TIMEOUT_SECONDS}). Exists so "
            "the hang path can be exercised deliberately, rather than being a bound "
            "nobody has ever seen fire."
        ),
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Server command, after --")
    args = parser.parse_args()

    # Strip only the leading separator: a server command may legitimately contain
    # `--` of its own, and dropping those would silently change what we launch.
    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
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
        initialised = _read_response(proc, 1, args.timeout)
        if not initialised or "result" not in initialised:
            print(
                "smoke: FAIL — no initialize result. The server either exited "
                "without answering (what a failed import looks like) or hung; the "
                "line above says which.",
                file=sys.stderr,
            )
            return 1
        print(f"smoke: initialize OK — serverInfo={initialised['result'].get('serverInfo')}")

        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        listed = _read_response(proc, 2, args.timeout)
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
        # Even without an expected count, zero tools is never a working server —
        # otherwise an empty registration would pass this check silently.
        if not names:
            print("smoke: FAIL — the server registered no tools at all.", file=sys.stderr)
            return 1
    finally:
        # The server has told us what we needed, so end it rather than waiting on
        # it: stdout is still a pipe we have stopped draining, and a slow exit
        # would stall here for no benefit.
        if proc.stdin is not None:
            proc.stdin.close()
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("smoke: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
