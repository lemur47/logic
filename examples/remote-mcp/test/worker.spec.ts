/**
 * Worker-level tests: bearer auth behaviour and the MCP JSON-RPC surface.
 *
 * Runs in plain Node (vitest) — the handler only uses WHATWG/webcrypto APIs
 * that Node 22 and the Workers runtime share.
 */

import { describe, expect, it } from "vitest";
import worker, { type Env } from "../src/index";

const SECRET = "test-secret-token";
const ENV: Env = { AUTH_TOKEN: SECRET };
const BASE = "https://poc.test";

function mcpRequest(body: unknown, token: string | null = SECRET): Request {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token !== null) {
    headers.Authorization = `Bearer ${token}`;
  }
  return new Request(`${BASE}/mcp`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
}

function rpc(method: string, params: Record<string, unknown> = {}, id: number = 1) {
  return { jsonrpc: "2.0", id, method, params };
}

function restRequest(body: unknown, token: string | null = SECRET, method = "POST"): Request {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token !== null) {
    headers.Authorization = `Bearer ${token}`;
  }
  return new Request(`${BASE}/api/pert`, {
    method,
    headers,
    body: method === "GET" ? undefined : JSON.stringify(body),
  });
}

describe("bearer-token gate", () => {
  it("rejects requests without a token", async () => {
    const res = await worker.fetch(mcpRequest(rpc("tools/list"), null), ENV);
    expect(res.status).toBe(401);
  });

  it("rejects requests with a wrong token", async () => {
    const res = await worker.fetch(mcpRequest(rpc("tools/list"), "wrong-token"), ENV);
    expect(res.status).toBe(401);
  });

  it("fails closed when the secret is not configured", async () => {
    const res = await worker.fetch(mcpRequest(rpc("tools/list")), {});
    expect(res.status).toBe(503);
  });

  it("does not gate the root info page", async () => {
    const res = await worker.fetch(new Request(`${BASE}/`), ENV);
    expect(res.status).toBe(200);
    const body = (await res.json()) as { name: string };
    expect(body.name).toBe("pmorun-mcp-poc");
  });
});

describe("MCP protocol surface", () => {
  it("answers initialize with server info and a supported protocol version", async () => {
    const res = await worker.fetch(
      mcpRequest(rpc("initialize", { protocolVersion: "2025-06-18" })),
      ENV,
    );
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      result: { protocolVersion: string; serverInfo: { name: string }; capabilities: object };
    };
    expect(body.result.protocolVersion).toBe("2025-06-18");
    expect(body.result.serverInfo.name).toBe("pmorun-mcp-poc");
    expect(body.result.capabilities).toHaveProperty("tools");
  });

  it("accepts the initialized notification with 202", async () => {
    // Built literally: passing an explicit `undefined` id to rpc() would
    // trigger the default parameter and silently turn this into a request.
    const notification = { jsonrpc: "2.0", method: "notifications/initialized", params: {} };
    const res = await worker.fetch(mcpRequest(notification), ENV);
    expect(res.status).toBe(202);
  });

  it("lists exactly one tool", async () => {
    const res = await worker.fetch(mcpRequest(rpc("tools/list")), ENV);
    const body = (await res.json()) as { result: { tools: Array<{ name: string }> } };
    expect(body.result.tools).toHaveLength(1);
    expect(body.result.tools[0]?.name).toBe("estimate_task_duration");
  });

  it("computes a PERT estimate through tools/call", async () => {
    const res = await worker.fetch(
      mcpRequest(
        rpc("tools/call", {
          name: "estimate_task_duration",
          arguments: { optimistic: 2, most_likely: 4, pessimistic: 8 },
        }),
      ),
      ENV,
    );
    const body = (await res.json()) as {
      result: { isError: boolean; structuredContent: { textbook: { expected: number } } };
    };
    expect(body.result.isError).toBe(false);
    expect(body.result.structuredContent.textbook.expected).toBeCloseTo(4.33, 2);
  });

  it("returns a tool-level error for invalid estimates", async () => {
    const res = await worker.fetch(
      mcpRequest(
        rpc("tools/call", {
          name: "estimate_task_duration",
          arguments: { optimistic: 5, most_likely: 2, pessimistic: 8 },
        }),
      ),
      ENV,
    );
    const body = (await res.json()) as {
      result: { isError: boolean; content: Array<{ text: string }> };
    };
    expect(body.result.isError).toBe(true);
    expect(body.result.content[0]?.text).toContain("cannot exceed");
  });

  it("returns a tool-level error for non-numeric arguments", async () => {
    const res = await worker.fetch(
      mcpRequest(
        rpc("tools/call", {
          name: "estimate_task_duration",
          arguments: { optimistic: "two", most_likely: 4, pessimistic: 8 },
        }),
      ),
      ENV,
    );
    const body = (await res.json()) as { result: { isError: boolean } };
    expect(body.result.isError).toBe(true);
  });

  it("rejects unknown methods with -32601", async () => {
    const res = await worker.fetch(mcpRequest(rpc("resources/list")), ENV);
    const body = (await res.json()) as { error: { code: number } };
    expect(body.error.code).toBe(-32601);
  });

  it("rejects batch requests", async () => {
    const res = await worker.fetch(mcpRequest([rpc("ping", {}, 1), rpc("ping", {}, 2)]), ENV);
    const body = (await res.json()) as { error: { code: number } };
    expect(body.error.code).toBe(-32600);
  });

  it("rejects malformed JSON with -32700", async () => {
    const req = new Request(`${BASE}/mcp`, {
      method: "POST",
      headers: { Authorization: `Bearer ${SECRET}`, "Content-Type": "application/json" },
      body: "{not json",
    });
    const res = await worker.fetch(req, ENV);
    const body = (await res.json()) as { error: { code: number } };
    expect(body.error.code).toBe(-32700);
  });

  it("answers GET /mcp with 405 (stateless server, no SSE stream)", async () => {
    const req = new Request(`${BASE}/mcp`, {
      headers: { Authorization: `Bearer ${SECRET}` },
    });
    const res = await worker.fetch(req, ENV);
    expect(res.status).toBe(405);
  });
});

describe("REST surface", () => {
  const VALID = { optimistic: 2, most_likely: 4, pessimistic: 8 };

  it("rejects requests without a token", async () => {
    const res = await worker.fetch(restRequest(VALID, null), ENV);
    expect(res.status).toBe(401);
  });

  it("rejects requests with a wrong token", async () => {
    const res = await worker.fetch(restRequest(VALID, "wrong-token"), ENV);
    expect(res.status).toBe(401);
  });

  it("fails closed when the secret is not configured", async () => {
    const res = await worker.fetch(restRequest(VALID), {});
    expect(res.status).toBe(503);
  });

  it("computes a PERT estimate on POST /api/pert", async () => {
    const res = await worker.fetch(restRequest(VALID), ENV);
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      input: { optimistic: number };
      textbook: { expected: number };
      adjusted: null;
    };
    expect(body.input.optimistic).toBe(2);
    expect(body.textbook.expected).toBeCloseTo(4.33, 2);
    expect(body.adjusted).toBeNull();
  });

  it("returns 400 with the validation message for invalid estimates", async () => {
    const res = await worker.fetch(
      restRequest({ optimistic: 5, most_likely: 2, pessimistic: 8 }),
      ENV,
    );
    expect(res.status).toBe(400);
    const body = (await res.json()) as { error: string };
    expect(body.error).toContain("cannot exceed");
  });

  it("returns 400 for non-numeric fields", async () => {
    const res = await worker.fetch(
      restRequest({ optimistic: "two", most_likely: 4, pessimistic: 8 }),
      ENV,
    );
    expect(res.status).toBe(400);
  });

  it("returns 400 for a non-object body", async () => {
    const res = await worker.fetch(restRequest([1, 2, 3]), ENV);
    expect(res.status).toBe(400);
  });

  it("returns 400 for malformed JSON", async () => {
    const req = new Request(`${BASE}/api/pert`, {
      method: "POST",
      headers: { Authorization: `Bearer ${SECRET}`, "Content-Type": "application/json" },
      body: "{not json",
    });
    const res = await worker.fetch(req, ENV);
    expect(res.status).toBe(400);
  });

  it("answers GET /api/pert with 405", async () => {
    const res = await worker.fetch(restRequest(null, SECRET, "GET"), ENV);
    expect(res.status).toBe(405);
    expect(res.headers.get("Allow")).toBe("POST");
  });

  it("keeps unknown /api/ paths at 404", async () => {
    const req = new Request(`${BASE}/api/montecarlo`, {
      method: "POST",
      headers: { Authorization: `Bearer ${SECRET}`, "Content-Type": "application/json" },
      body: JSON.stringify(VALID),
    });
    const res = await worker.fetch(req, ENV);
    expect(res.status).toBe(404);
  });
});
