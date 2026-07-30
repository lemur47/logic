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
- With `PMORUN_DB` unset the server is byte-for-byte as stateless as 0.1.1, so
  existing users see no behaviour change from this release.

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
  now `mcp[cli]>=1.0,<2`.
- Monte Carlo: bounded the drift path and capped list inputs, closing a
  denial-of-service shape where a large or hostile request could force
  unbounded work.
- Tightened CORS handling in the HTTP-transport path.

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
