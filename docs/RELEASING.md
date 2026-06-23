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

## Cutting a release

1. Land all release content on `main` via PR (never tag a feature branch).
2. Bump `version` in `pyproject.toml` if it has not already been set for this
   release, and merge that to `main`.
3. Update the **documented install version** to match: the pinned
   `pmorun-mcp@<version>` / `pmorun-mcp==<version>` examples in
   `mcp_server/README.md` (the PyPI long description), plus the living homepage
   §03 and `docs/{en,ja}/mcp-server.md` install snippets. Leave the unpinned
   `uvx pmorun-mcp` lines as-is. This keeps the storefront from stranding new
   users on an older pin.
4. Tag the release commit on `main` and push the tag:
   ```bash
   git checkout main && git pull
   git tag v0.1.1      # match pyproject version, prefixed with v
   git push origin v0.1.1
   ```
5. The push triggers `release.yml`: it builds the sdist + wheel and publishes to
   PyPI via OIDC. Watch the run under the repo's **Actions** tab.
6. Verify: `uvx pmorun-mcp` from a clean machine should start the stdio server.

> **PyPI versions are immutable.** A version number can never be re-uploaded or
> reused once published — even after deletion. Double-check the version and that
> the build is correct before pushing the tag.
