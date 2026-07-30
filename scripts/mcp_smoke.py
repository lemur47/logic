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

Reading the stream
------------------
Frames are read with ``os.read`` into a buffer this module owns, and split on
newlines here. That is deliberate, and the first attempt got it wrong in a way
worth recording: it selected on the pipe and then called ``readline()`` on a
``TextIOWrapper``. Readiness of the file descriptor says nothing about the state
of Python's own buffer above it, so that combination had two failure modes — a
partial line left ``readline()`` blocking past the timeout (the hang the bound was
added to prevent), and two frames arriving in one write left the second sitting in
the buffer while ``select`` waited for OS data that never came, reporting "not
answering" about a server that had answered. Owning the buffer removes both: the
descriptor is the only reader, so readiness is meaningful, and partial frames
accumulate instead of blocking.

Usage
-----
    python scripts/mcp_smoke.py [--expect-tools N] [--timeout S] -- <command> [args...]

    python scripts/mcp_smoke.py -- pmorun-mcp
    python scripts/mcp_smoke.py --expect-tools 4 -- uvx --refresh pmorun-mcp

Exit status is 0 only if the server completed the handshake and listed tools.
"""

from __future__ import annotations

import argparse
import json
import os
import selectors
import subprocess
import sys
import time

# Generous, because a cold `uvx` run resolves and downloads from PyPI first. This
# bounds the wait for each response: a server that starts but never answers — a
# hung resolve, a blocking network call, something waiting on a prompt — must fail
# this check rather than hang it.
TIMEOUT_SECONDS = 300

READ_CHUNK = 65536


class FrameReader:
    """Newline-delimited JSON frames from a pipe, with a wait that actually bounds.

    Holds its own buffer, so leftover frames from a batched write survive between
    calls. ``reason`` records why a read gave up, for the caller's diagnostics.
    """

    def __init__(self, fileno: int) -> None:
        self._fileno = fileno
        self._buffer = b""
        self._selector = selectors.DefaultSelector()
        self._selector.register(fileno, selectors.EVENT_READ)
        self.reason: str | None = None

    def close(self) -> None:
        self._selector.close()

    def next_frame(self, deadline: float) -> bytes | None:
        """Return the next complete frame, or None on EOF or deadline."""
        while True:
            newline = self._buffer.find(b"\n")
            if newline >= 0:
                frame, self._buffer = self._buffer[:newline], self._buffer[newline + 1 :]
                return frame

            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self._selector.select(timeout=remaining):
                self.reason = "timeout"
                return None

            chunk = os.read(self._fileno, READ_CHUNK)
            if not chunk:  # EOF — the server closed stdout, i.e. it died
                self.reason = "eof"
                return None
            self._buffer += chunk


def _send(proc: subprocess.Popen[bytes], message: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write((json.dumps(message) + "\n").encode())
    proc.stdin.flush()


def _read_response(reader: FrameReader, want_id: int, timeout: float) -> dict | None:
    """Read frames until the response carrying ``want_id`` arrives.

    Skips notifications and log frames, which share the stream with responses and
    are not errors. The deadline covers the whole wait for this response, not each
    individual read, so a chatty server cannot extend it indefinitely.
    """
    deadline = time.monotonic() + timeout
    while True:
        frame = reader.next_frame(deadline)
        if frame is None:
            return None
        stripped = frame.strip()
        if not stripped:
            continue
        try:
            message = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(message, dict) and message.get("id") == want_id:
            return message


def _explain(reader: FrameReader, what: str, timeout: float) -> None:
    if reader.reason == "timeout":
        print(
            f"smoke: FAIL — no {what} within {timeout}s. The server started and is not answering.",
            file=sys.stderr,
        )
    else:
        print(
            f"smoke: FAIL — no {what}; the server closed its output without "
            "answering, which is what a failed import looks like.",
            file=sys.stderr,
        )


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
            f"Seconds to wait for each response (default {TIMEOUT_SECONDS}). Exposed so "
            "the give-up paths can be exercised deliberately, rather than being a bound "
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
    )
    assert proc.stdout is not None
    reader = FrameReader(proc.stdout.fileno())

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
        initialised = _read_response(reader, 1, args.timeout)
        if initialised is None:
            _explain(reader, "initialize response", args.timeout)
            return 1
        if "result" not in initialised:
            print(f"smoke: FAIL — initialize returned an error: {initialised}", file=sys.stderr)
            return 1
        print(f"smoke: initialize OK — serverInfo={initialised['result'].get('serverInfo')}")

        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        listed = _read_response(reader, 2, args.timeout)
        if listed is None:
            _explain(reader, "tools/list response", args.timeout)
            return 1
        if "result" not in listed:
            print(f"smoke: FAIL — tools/list returned an error: {listed}", file=sys.stderr)
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
        # it: stdout is a pipe we have stopped draining, and a slow exit would
        # stall here for no benefit. Every verdict above is already decided.
        reader.close()
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
