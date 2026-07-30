# Releasing `pmorun-mcp` to PyPI

The MCP server is published to [PyPI](https://pypi.org/) as `pmorun-mcp` via a
tag-triggered GitHub Actions workflow ([`.github/workflows/release.yml`](../.github/workflows/release.yml))
using **OIDC Trusted Publishing** — no long-lived API token is stored anywhere.

## One-time setup (repository owner, on PyPI)

This must be done once before the first release. It cannot be automated from the
repo — it requires a logged-in PyPI account with rights to the project name.

1. Sign in at [pypi.org](https://pypi.org/).
2. Because `pmorun-mcp` has not been published yet, add a **pending** trusted
   publisher: **Your account → Publishing → Add a new pending publisher**.
   (After the first release this becomes a normal trusted publisher under the
   project's *Manage → Publishing* settings.)
3. Fill in, exactly:
   - **PyPI Project Name:** `pmorun-mcp`
   - **Owner:** `lemur47`
   - **Repository name:** `logic`
   - **Workflow name:** `release.yml`
   - **Environment name:** `pypi`
4. In GitHub, create the matching deployment environment:
   **Settings → Environments → New environment → `pypi`**. Optionally add a
   required reviewer so a human approves each publish.

No secrets are added to the repository. The workflow's `id-token: write`
permission lets the `publish` job mint a short-lived OIDC token that PyPI
exchanges for scoped upload rights.

### Optional one-time setup for TestPyPI rehearsals

`release.yml` can be dispatched manually to rehearse the pipeline. Two targets:

- **`none`** (the default) — builds, validates metadata, round-trips the artifact,
  then installs the wheel with dependencies resolved fresh and drives a real MCP
  handshake. **Needs no setup at all**, and exercises everything except the
  publish action itself. Use this after any change to the workflow.
- **`testpypi`** — additionally uploads to TestPyPI, which is the only way to
  exercise `gh-action-pypi-publish` without consuming a real, immutable version.

The `testpypi` target requires the same trusted-publisher dance as above, on
[test.pypi.org](https://test.pypi.org/) instead, with **Environment name:
`testpypi`** — plus a matching `testpypi` GitHub environment. Until that exists,
the target will fail at the publish step; the `none` target is unaffected.

Production PyPI is deliberately **not** offered as a dispatch target. Only a tag
push can publish for real, so a mis-clicked rehearsal cannot burn a version.

## Cutting a release

1. Land all release content on `main` via PR (never tag a feature branch).
2. Bump `version` in `pyproject.toml` if it has not already been set for this
   release, and merge that to `main`.
3. **Write the [`CHANGELOG.md`](../CHANGELOG.md) entry** for the version, in the
   same PR as the bump. Derive it from `git log v<previous>..HEAD -- mcp_server app`
   — those are the paths the wheel ships (`pyproject.toml`'s `packages`), so a
   commit outside them is not part of the release. Give release dates from the tag
   or the PyPI upload time, never from memory.

   Ask of every entry: **does this change what a user of the MCP server
   experiences?** A fix inside `app/` may ship in the wheel and still be
   unreachable without the `app` extra — say so rather than implying the server
   changed. And do not write "no behaviour change" without checking the input
   bounds and validation limits, which apply to the default surface and are the
   easiest thing to overlook.

4. **Replace `Unreleased` in the changelog heading with the release date** before
   tagging. Nothing enforces this — the build guard compares the tag to
   `pyproject.toml` only — so a release can otherwise publish with its own entry
   still marked unreleased.
5. Update the **documented install version** to match: the pinned
   `pmorun-mcp@<version>` / `pmorun-mcp==<version>` examples in
   `mcp_server/README.md` (the PyPI long description), plus the living homepage
   §03 and `docs/{en,ja}/mcp-server.md` install snippets. Leave the unpinned
   `uvx pmorun-mcp` lines as-is. This keeps the storefront from stranding new
   users on an older pin.

   Search for `v0.1`-style **prose** as well as the exact old version string.
   Docstrings and marketing copy carry version claims and tool counts that a
   `<version>` grep cannot see, and they have survived releases before. Prefer
   wording that states a *condition* over wording that states a count, so the
   next release does not have to touch the same lines again.

   **Read `mcp_server/README.md` from the top.** It is the PyPI project page, its
   opening blockquote is the most-read paragraph the project has, and a sweep
   driven by grep hits will skip it. Check its internal anchors still resolve if
   you renamed any heading — `twine check` validates rendering, not links.
6. **Rehearse the publish against TestPyPI** using `release.yml`'s
   `workflow_dispatch` trigger, and let it go green before you tag. The
   tag-triggered path is the only consumer of that workflow, so a change to it is
   otherwise unexercised until the moment it matters. Note what a rehearsal does
   and does not cover: `target: none` skips the `publish` job entirely, so only
   `target: testpypi` exercises the publish action, its environment and its
   repository URL.
7. Tag the release commit on `main` and push the tag:
   ```bash
   git checkout main && git pull
   git tag v0.2.0      # match pyproject version, prefixed with v
   git push origin v0.2.0
   ```
8. The push triggers `release.yml`: it builds the sdist + wheel and publishes to
   PyPI via OIDC. Watch the run under the repo's **Actions** tab. If the `pypi`
   environment has a required reviewer, the publish job **pauses for approval** —
   that is the gate working, not a failure.
9. **Verify the published artefact by making it answer, not by watching it start.**
   Resolve it the way a user does — fresh, with no lockfile in the picture — pinned
   to the version you just published, and drive a real MCP handshake:
   ```bash
   python scripts/mcp_smoke.py --expect-tools 4 -- \
     uvx --refresh --from "pmorun-mcp==0.2.0" pmorun-mcp
   ```
   **Pin the version in the command.** That is what proves you tested the release
   rather than whatever was already cached — the `serverInfo.version` in the
   handshake is the **mcp SDK's** version, not ours (`FastMCP()` is constructed
   without one), so it cannot tell 0.2.0 from 0.1.1.

   A server whose import fails exits silently, and every client reports that as
   nothing more than "connection closed". "The process did not immediately exit"
   is therefore not evidence that the release works.

> **Why step 9 is worded that way.** 0.1.1 shipped with `mcp[cli]>=1.0` and no
> upper bound. When `mcp` 2.0.0 removed `FastMCP`, every fresh install of the
> published wheel began dying at import — on every machine — while CI stayed green,
> because `uv.lock` pins a working `mcp`. **A lockfile proves the repository works;
> it never proves the release works.** Only an unlocked resolve of the published
> artefact tests what a user actually gets.

> **PyPI versions are immutable.** A version number can never be re-uploaded or
> reused once published — even after deletion. Double-check the version and that
> the build is correct before pushing the tag.
