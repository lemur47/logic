/**
 * Minimal MCP server over Streamable HTTP — stateless JSON responses only.
 *
 * Implements exactly the JSON-RPC subset a tools-only MCP server needs
 * (initialize, the initialized notification, ping, tools/list, tools/call),
 * with no SDK dependency. Session management and SSE streaming are deliberately
 * out of scope: every request is independent and answered with
 * `application/json`, which the Streamable HTTP transport permits.
 */

import { calculateTask } from "./pert";

const SERVER_INFO = { name: "pmorun-mcp-poc", version: "0.1.0" };

/** Protocol revisions this server knows; newest first. */
const SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"];

const TOOLS = [
  {
    name: "estimate_task_duration",
    description:
      "Estimate how long a single task will take from a three-point (PERT) estimate. " +
      "Textbook PERT only: expected = (O + 4M + P) / 6, std_dev = (P - O) / 6, plus the " +
      "68/95/99% confidence ranges. Unit-agnostic - results use whatever time unit the " +
      "estimates use. PoC subset of the pmorun-mcp stdio tool: no insight tags.",
    inputSchema: {
      type: "object",
      properties: {
        optimistic: { type: "number", description: "Best-case duration (O). O <= M <= P, all >= 0." },
        most_likely: { type: "number", description: "Most probable duration (M)." },
        pessimistic: { type: "number", description: "Worst-case duration (P)." },
      },
      required: ["optimistic", "most_likely", "pessimistic"],
      additionalProperties: false,
    },
  },
];

interface JsonRpcRequest {
  jsonrpc?: string;
  id?: number | string | null;
  method?: string;
  params?: Record<string, unknown>;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function rpcResult(id: number | string | null, result: unknown): Response {
  return jsonResponse({ jsonrpc: "2.0", id, result });
}

function rpcError(id: number | string | null, code: number, message: string): Response {
  return jsonResponse({ jsonrpc: "2.0", id, error: { code, message } });
}

function toolError(id: number | string | null, message: string): Response {
  return rpcResult(id, {
    content: [{ type: "text", text: message }],
    isError: true,
  });
}

function handleInitialize(msg: JsonRpcRequest): Response {
  const requested = (msg.params?.protocolVersion as string) ?? "";
  const protocolVersion = SUPPORTED_PROTOCOL_VERSIONS.includes(requested)
    ? requested
    : SUPPORTED_PROTOCOL_VERSIONS[0];
  return rpcResult(msg.id ?? null, {
    protocolVersion,
    capabilities: { tools: {} },
    serverInfo: SERVER_INFO,
  });
}

function handleToolsCall(msg: JsonRpcRequest): Response {
  const id = msg.id ?? null;
  const name = msg.params?.name;
  if (name !== "estimate_task_duration") {
    return rpcError(id, -32602, `Unknown tool: ${String(name)}`);
  }

  const args = (msg.params?.arguments ?? {}) as Record<string, unknown>;
  for (const field of ["optimistic", "most_likely", "pessimistic"]) {
    if (typeof args[field] !== "number") {
      return toolError(id, `Invalid arguments: '${field}' must be a number.`);
    }
  }

  try {
    const result = calculateTask(
      args.optimistic as number,
      args.most_likely as number,
      args.pessimistic as number,
    );
    return rpcResult(id, {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      structuredContent: result,
      isError: false,
    });
  } catch (err) {
    if (err instanceof RangeError) {
      return toolError(id, `Invalid estimate: ${err.message}`);
    }
    throw err;
  }
}

/** Handle one Streamable HTTP POST carrying a single JSON-RPC message. */
export async function handleMcpPost(request: Request): Promise<Response> {
  let msg: JsonRpcRequest;
  try {
    msg = (await request.json()) as JsonRpcRequest;
  } catch {
    return rpcError(null, -32700, "Parse error: body is not valid JSON");
  }

  if (Array.isArray(msg)) {
    return rpcError(null, -32600, "Batch requests are not supported");
  }
  if (msg.jsonrpc !== "2.0" || typeof msg.method !== "string") {
    return rpcError(msg.id ?? null, -32600, "Invalid JSON-RPC 2.0 request");
  }

  // Notifications get 202 Accepted with no body, per Streamable HTTP.
  if (msg.id === undefined) {
    return new Response(null, { status: 202 });
  }

  switch (msg.method) {
    case "initialize":
      return handleInitialize(msg);
    case "ping":
      return rpcResult(msg.id ?? null, {});
    case "tools/list":
      return rpcResult(msg.id ?? null, { tools: TOOLS });
    case "tools/call":
      return handleToolsCall(msg);
    default:
      return rpcError(msg.id ?? null, -32601, `Method not found: ${msg.method}`);
  }
}
