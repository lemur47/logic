# Changelog

All notable changes to `pmorun-mcp` are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

This file covers the **published package** — the lean stdio MCP server on PyPI.
It is not a log of every repository commit; the FastAPI prototype in `app/`, the
site and the examples move independently and are not part of the release surface
except where the wheel ships them.

## [0.2.0] — Unreleased

### Added

- **Opt-in calibration memory, backed by a local SQLite file.** Set `PMORUN_DB`
  to a writable path and four further tools register: `record_estimate`,
  `record_actual`, `summarise_calibration`, and `estimate_from_history` — the
  last of which had been parked since 0.1 waiting for exactly this data source.
  The tool surface is therefore **conditional**: four tools by default, eight
  when `PMORUN_DB` is set.
- With `PMORUN_DB` unset the server remains **stateless** — nothing is written
  anywhere, and the four classic tools are the whole surface, exactly as in 0.1.1.
  That is not the same as "no behaviour change": see the input bounds under
  *Fixed*, which apply to the default surface too.

> **Read before enabling it.** The calibration database is a plain, **unencrypted**
> local SQLite file. Do not point `PMORUN_DB` at a shared, synced or backed-up
> directory unless you intend its contents to travel there. See the storage
> section of the README.

### Fixed

- **The published 0.1.1 could not start at all once `mcp` 2.0.0 was released, and
  this release is the fix.** `mcp` 2.0.0 removed `FastMCP`, which the server
  imports, and the dependency was declared without an upper bound — so a fresh
  install resolved 2.0.0 and died at import with
  `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`. The requirement is
  now **`mcp[cli]>=1.2,<2`**. Both bounds carry weight: `mcp.server.fastmcp` first
  appears in 1.2.0, so every release below it fails in exactly the same way (and
  declares no extras at all, making `mcp[cli]` unsatisfiable there), while 2.x no
  longer has it. The range is precisely the versions that contain what the server
  imports.
- **Compatibility note across that range.** `mcp` 1.2.0 does not emit
  `outputSchema` on `tools/list` or `structuredContent` on `tools/call`; recent 1.x
  does. Both are legal installs of 0.2.0, so a client that reads
  `structuredContent` gets it from a newer resolve and falls back to text content
  on an older one. Pin a recent `mcp` if your client depends on the structured
  form.
- Monte Carlo: bounded the drift path and capped list inputs, closing a
  denial-of-service shape where a large or hostile request could force unbounded
  work. **This changes behaviour on the default surface**, so it is an upgrade
  note as much as a fix: list fields (`tasks`, `depends_on`, `risk_classes`) now
  accept at most 1000 items, and a simulation is rejected when
  `tasks × num_simulations` exceeds 10,000,000. Requests above either limit
  returned a result in 0.1.1 and now return a validation error. Both limits are
  far above any real project plan; if you are over one, you were almost certainly
  not getting a meaningful answer either.
- Tightened CORS handling in `app.main`. This affects only the self-host FastAPI
  prototype: the module ships in the wheel but needs the `app` extra to import,
  and the MCP server has no HTTP transport to apply it to. Listed for completeness
  because the code is in the distribution, not because it changes anything for
  users of the MCP server.

### Changed

- Internal only, with no change to the tool surface or to any result shape: the
  Monte Carlo simulation paths now share one forward pass and one summariser, and
  both transports share one tag resolver and one result converter.

## [0.1.1] — 2026-06-23

Packaging and documentation fixes over 0.1.0. Four tools over stdio:
`estimate_task_duration`, `identify_schedule_risk`,
`compare_investment_options`, `evaluate_project_health`.

> **This version no longer works.** It is unusable on any machine from the moment
> `mcp` 2.0.0 reached PyPI — see the 0.2.0 *Fixed* entry above. If you pinned
> `pmorun-mcp@0.1.1`, move to 0.2.0. To stay on 0.1.1 you must constrain the
> dependency yourself, for example
> `uvx --with "mcp[cli]<2" pmorun-mcp@0.1.1`.

## [0.1.0] — 2026-06-09

First publication to PyPI. The four classic PMO decision tools — PERT estimation,
Monte Carlo schedule risk, TCO comparison and earned-value project health — over
the Model Context Protocol, stdio transport, no authentication and no hosted
component.
