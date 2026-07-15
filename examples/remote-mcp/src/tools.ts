/**
 * Shared tool execution seam — the one place arguments are validated and the
 * core is called, whatever the transport.
 *
 * Both surfaces (MCP JSON-RPC in mcp.ts, plain REST in rest.ts) accept an
 * untyped JSON object, pass it here, and map the outcome onto their own error
 * vocabulary: MCP wraps failures as tool-level errors (isError: true, HTTP
 * 200); REST turns the same message into an HTTP 400 body. Keeping the
 * validation and messages here means the two surfaces cannot drift apart.
 */

import { calculateTask, type TaskEstimation } from "./pert";

export type ToolOutcome =
  | { ok: true; result: TaskEstimation }
  | { ok: false; message: string };

/** Validate raw JSON arguments and run the PERT estimate. Never throws for bad input. */
export function runEstimateTaskDuration(args: Record<string, unknown>): ToolOutcome {
  for (const field of ["optimistic", "most_likely", "pessimistic"]) {
    if (typeof args[field] !== "number") {
      return { ok: false, message: `Invalid arguments: '${field}' must be a number.` };
    }
  }

  try {
    const result = calculateTask(
      args.optimistic as number,
      args.most_likely as number,
      args.pessimistic as number,
    );
    return { ok: true, result };
  } catch (err) {
    if (err instanceof RangeError) {
      return { ok: false, message: `Invalid estimate: ${err.message}` };
    }
    throw err;
  }
}
