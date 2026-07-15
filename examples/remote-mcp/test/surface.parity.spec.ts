/**
 * Cross-surface parity: for identical inputs, the REST body must equal the MCP
 * structuredContent exactly (same core, same JSON), and both must match the
 * Python-generated fixtures within the rounding tolerance the core parity
 * suite already documents. Error parity is checked too: an invalid input must
 * produce the same message on both surfaces, just wrapped differently
 * (MCP tool-level error vs REST HTTP 400).
 */

import { describe, expect, it } from "vitest";
import worker, { type Env } from "../src/index";
import fixtures from "./fixtures/pert-parity.json";

const SECRET = "test-secret-token";
const ENV: Env = { AUTH_TOKEN: SECRET };
const BASE = "https://poc.test";

interface PertArgs {
  optimistic: number;
  most_likely: number;
  pessimistic: number;
}

async function callMcp(args: unknown): Promise<Response> {
  return worker.fetch(
    new Request(`${BASE}/mcp`, {
      method: "POST",
      headers: { Authorization: `Bearer ${SECRET}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: { name: "estimate_task_duration", arguments: args },
      }),
    }),
    ENV,
  );
}

async function callRest(body: unknown): Promise<Response> {
  return worker.fetch(
    new Request(`${BASE}/api/pert`, {
      method: "POST",
      headers: { Authorization: `Bearer ${SECRET}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    ENV,
  );
}

describe("REST and MCP surfaces return identical results from the shared core", () => {
  for (const { args } of fixtures.cases as Array<{ args: PertArgs }>) {
    it(`O=${args.optimistic} M=${args.most_likely} P=${args.pessimistic}`, async () => {
      const [mcpRes, restRes] = await Promise.all([callMcp(args), callRest(args)]);
      expect(mcpRes.status).toBe(200);
      expect(restRes.status).toBe(200);

      const mcpBody = (await mcpRes.json()) as {
        result: { isError: boolean; structuredContent: unknown };
      };
      const restBody = (await restRes.json()) as unknown;

      expect(mcpBody.result.isError).toBe(false);
      // Same core, same JSON serialisation — equality is exact, not approximate.
      // (Fixture-tolerance checks live in pert.parity.spec.ts; repeating them
      // here would only re-test the core.)
      expect(restBody).toEqual(mcpBody.result.structuredContent);
    });
  }
});

describe("error parity: one validation message, two wrappings", () => {
  const invalid = { optimistic: 5, most_likely: 2, pessimistic: 8 };

  it("wraps the same message as MCP tool error and REST 400", async () => {
    const [mcpRes, restRes] = await Promise.all([callMcp(invalid), callRest(invalid)]);

    expect(mcpRes.status).toBe(200); // MCP reports tool failures in-band
    expect(restRes.status).toBe(400); // REST reports them as HTTP status

    const mcpBody = (await mcpRes.json()) as {
      result: { isError: boolean; content: Array<{ text: string }> };
    };
    const restBody = (await restRes.json()) as { error: string };

    expect(mcpBody.result.isError).toBe(true);
    expect(restBody.error).toBe(mcpBody.result.content[0]?.text);
  });

  it("agrees on non-numeric arguments too", async () => {
    const bad = { optimistic: "two", most_likely: 4, pessimistic: 8 };
    const [mcpRes, restRes] = await Promise.all([callMcp(bad), callRest(bad)]);

    const mcpBody = (await mcpRes.json()) as {
      result: { isError: boolean; content: Array<{ text: string }> };
    };
    const restBody = (await restRes.json()) as { error: string };

    expect(restRes.status).toBe(400);
    expect(mcpBody.result.isError).toBe(true);
    expect(restBody.error).toBe(mcpBody.result.content[0]?.text);
  });
});
