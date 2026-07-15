/**
 * Plain REST surface over the same core — one route, POST /api/pert.
 *
 * The request body is the same JSON object the MCP tool takes as arguments
 * ({ optimistic, most_likely, pessimistic }); the 200 response body is the
 * same TaskEstimation object MCP returns as structuredContent. Where MCP
 * reports failures in-band (tool-level error, HTTP 200), REST collapses every
 * failure onto HTTP status codes: 400 for anything wrong with the input,
 * 405 for anything but POST. Auth (401/503) is enforced by the entry point,
 * identically for both surfaces.
 */

import { runEstimateTaskDuration } from "./tools";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Handle one POST /api/pert request. */
export async function handleRestPert(request: Request): Promise<Response> {
  if (request.method !== "POST") {
    return new Response(null, { status: 405, headers: { Allow: "POST" } });
  }

  let args: Record<string, unknown>;
  try {
    const parsed: unknown = await request.json();
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return jsonResponse({ error: "Body must be a JSON object" }, 400);
    }
    args = parsed as Record<string, unknown>;
  } catch {
    return jsonResponse({ error: "Body is not valid JSON" }, 400);
  }

  const outcome = runEstimateTaskDuration(args);
  if (!outcome.ok) {
    return jsonResponse({ error: outcome.message }, 400);
  }
  return jsonResponse(outcome.result);
}
