/**
 * pmorun-mcp-poc — Cloudflare Worker entry point.
 *
 * OSS proof of concept: pmo.run decision logic served over remote MCP
 * (Streamable HTTP). Stateless by design — no KV, no D1, no R2, no logs of
 * request content. Access is gated by a shared-secret bearer token held as a
 * Worker secret (AUTH_TOKEN); the worker fails closed if the secret is unset.
 */

import { handleMcpPost } from "./mcp";
import { handleRestPert } from "./rest";

export interface Env {
  AUTH_TOKEN?: string;
}

/**
 * Constant-time bearer comparison: hash both sides with SHA-256 and compare
 * digests, so comparison time is independent of where the strings differ.
 */
async function isAuthorized(request: Request, secret: string): Promise<boolean> {
  const header = request.headers.get("Authorization") ?? "";
  if (!header.startsWith("Bearer ")) {
    return false;
  }
  const presented = header.slice("Bearer ".length).trim();
  const encoder = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(presented)),
    crypto.subtle.digest("SHA-256", encoder.encode(secret)),
  ]);
  const av = new Uint8Array(a);
  const bv = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < av.length; i++) {
    diff |= (av[i] ?? 0) ^ (bv[i] ?? 0);
  }
  return diff === 0;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/" && request.method === "GET") {
      return new Response(
        JSON.stringify({
          name: "pmorun-mcp-poc",
          notice:
            "Proof of concept, no SLA. Open-source core of pmo.run served over remote MCP " +
            "(Streamable HTTP) and plain REST from one core. MCP endpoint: POST /mcp; " +
            "REST endpoint: POST /api/pert (bearer token required for both). " +
            "Self-host it yourself: https://github.com/lemur47/logic",
        }),
        { headers: { "Content-Type": "application/json" } },
      );
    }

    // Both surfaces sit behind the same gate: identical fail-closed behaviour,
    // identical constant-time bearer check. Only the payload shape differs.
    if (url.pathname === "/mcp" || url.pathname === "/api/pert") {
      // Fail closed: an undeployed/unset secret must never mean an open endpoint.
      if (!env.AUTH_TOKEN) {
        return new Response(JSON.stringify({ error: "Server not configured" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (!(await isAuthorized(request, env.AUTH_TOKEN))) {
        return new Response(JSON.stringify({ error: "Unauthorized" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.pathname === "/api/pert") {
        return handleRestPert(request);
      }
      if (request.method === "POST") {
        return handleMcpPost(request);
      }
      // Stateless server: no SSE stream to offer on GET, nothing to DELETE.
      return new Response(null, { status: 405, headers: { Allow: "POST" } });
    }

    return new Response(JSON.stringify({ error: "Not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  },
};
