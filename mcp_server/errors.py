"""
Structured, LLM-facing error types for the pmo-logic MCP tools.

FastMCP surfaces a raised exception to the client as ``str(exc)`` only — never a
Python traceback (see ``mcp.server.lowlevel.server._make_error_result``). We lean
on that: every tool error stringifies as ``[<ErrorType>] <message>`` so the model
receives a tagged, human-readable reason it can act on, with no stack trace and no
internals leaked across the wire.
"""

from __future__ import annotations

import functools
from collections.abc import Callable

from pydantic import ValidationError as PydanticValidationError


class ToolError(Exception):
    """Base for all pmo-logic tool errors.

    Subclasses set ``error_type``; the string form is ``[<error_type>] <message>``
    so the tag travels with the message FastMCP returns to the client.
    """

    error_type = "ToolError"

    def __str__(self) -> str:
        return f"[{self.error_type}] {super().__str__()}"


class ToolValidationError(ToolError):
    """Inputs are each individually valid but jointly inconsistent (e.g. an
    optimistic estimate larger than the most-likely one), or are otherwise
    rejected before any computation runs."""

    error_type = "ValidationError"


class ToolComputationError(ToolError):
    """The underlying calculation rejected the inputs — for example a dependency
    cycle in a schedule, or a non-positive budget at completion."""

    error_type = "ComputationError"


class ToolInternalError(ToolError):
    """An unexpected failure. The message is deliberately generic so no internal
    state leaks to the client; the original cause is chained for server-side logs."""

    error_type = "InternalError"


def _summarise_pydantic(exc: PydanticValidationError) -> str:
    """Flatten a Pydantic error into one tidy, location-tagged line per problem."""
    parts = []
    for err in exc.errors():
        location = ".".join(str(part) for part in err["loc"]) or "(root)"
        parts.append(f"{location}: {err['msg']}")
    return "; ".join(parts)


def structured_errors[F: Callable[..., object]](fn: F) -> F:
    """Wrap a tool so every failure leaves as a tagged :class:`ToolError`.

    - Already-tagged :class:`ToolError`\\ s pass through untouched.
    - Pydantic validation failures become :class:`ToolValidationError`.
    - Domain ``ValueError``/``KeyError`` from the core layer become
      :class:`ToolComputationError`.
    - Anything else becomes a generic :class:`ToolInternalError` (no detail leaked).

    ``functools.wraps`` preserves the wrapped function's name, docstring, and
    annotations, which FastMCP introspects to build the tool's input/output schema.
    """

    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        try:
            return fn(*args, **kwargs)
        except ToolError:
            raise
        except PydanticValidationError as exc:
            raise ToolValidationError(_summarise_pydantic(exc)) from exc
        except (ValueError, KeyError) as exc:
            raise ToolComputationError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 — last-resort guard; no traceback leaks
            raise ToolInternalError("An unexpected error occurred while running the tool.") from exc

    return wrapper  # type: ignore[return-value]
