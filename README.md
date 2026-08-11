# splunk-app-ci

Shared CI/CD tooling for Apius Splunk apps: a reusable GitHub Actions workflow
plus a small Python module for version stamping and Splunkbase packaging.

## Reusable PR-gate workflow

`.github/workflows/app-ci.yml` is a `workflow_call` workflow every app repo
invokes. It runs ruff (lint + format check), `pytest` when a `tests/`
directory is present, and Splunk AppInspect (base checks) against the app
directory.

Caller example (`.github/workflows/ci.yml` in an app repo):

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  pr-gate:
    uses: apius-tech/splunk-app-ci/.github/workflows/app-ci.yml@main
    with:
      app_id: <the app id == the app directory name>
```

Pin `@main` for now; repin to a released tag (e.g. `@v1`) once one is cut.

Inputs:
- `app_id` (required) — the app id, which is also the app's directory name and
  the AppInspect target.
- `python_version` (optional, default `3.9`) — Python used for the tooling.

## Packaging module

`splunk_app_ci` provides version stamping and Splunkbase packaging, used by the
release workflow.

```
# build the Splunkbase artifact (stamps app.conf inside the package)
python -m splunk_app_ci package --app-dir <app_id> --version X.Y.Z --dest dist

# stamp version into source files in place (app.conf + pyproject.toml)
python -m splunk_app_ci stamp --version X.Y.Z \
    --app-conf <app_id>/default/app.conf --pyproject pyproject.toml

# print the version currently stamped in app.conf (how the release workflow
# derives the version instead of a human retyping it into a tag)
python -m splunk_app_ci current-version --app-conf <app_id>/default/app.conf
```

`build_package` produces `<app_id>-<version>.tar.gz` whose single top-level
directory is the app id, with `app.conf` version stamped, vendored `lib/`
retained, and tooling/VCS artifacts excluded.

## Release workflows

Two reusable workflows implement the commit-back release-PR flow (ADR-0004),
each with a thin caller in the app repo:

- `.github/workflows/prepare-release.yml` (`workflow_call`; inputs `version`,
  `app_id`) — stamps `app.conf [launcher] version` and root `pyproject.toml
  [project].version` to `version` on a `release/vX.Y.Z` branch and opens a
  "Release vX.Y.Z" PR. It never writes to main directly; opening the PR runs
  the normal PR gate.
- `.github/workflows/release.yml` (`workflow_call`; inputs `app_id`, `version`
  optional, `cloud_gate` default `false`, `splunk_versions` required,
  `splunkbase_app_id`; secrets `SPLUNK_USER`/`SPLUNK_PASS`) — packages the app
  at the released version, runs Splunk AppInspect via the **AppInspect API**
  (`splunk/appinspect-api-action`), publishes a GitHub Release with the
  `.tar.gz` and auto-generated notes, then promotes that same artifact to
  Splunkbase behind the caller's `splunkbase` Environment approval (ADR-0006).
  Base (non-cloud) errors/failures block; cloud findings are advisory unless
  `cloud_gate=true` (ADR-0005).

### Human release flow

1. Dispatch the app's `prepare-release` caller with the target version
   (`X.Y.Z`). This opens the "Release vX.Y.Z" PR.
2. Review and merge the Release PR — main now shows the released version, and
   merging is what triggers the release: package -> AppInspect API -> tag ->
   GitHub Release.
3. Approve the `splunkbase` deployment to publish. Leaving it unapproved is a
   valid outcome: the GitHub Release stands and nothing is uploaded.

No tag is pushed by hand. The `release` job creates `vX.Y.Z` itself via
`gh release create --target`, because a tag pushed with `GITHUB_TOKEN` does not
trigger `on: push: tags` — minting the tag in the run that already has the
package avoids both the second event and a PAT.

The version is derived, never retyped: `prepare-release` stamps it into
`app.conf`, and the release reads it back with `current-version`. A push to main
that does not change the version, or a re-run of one that does, is a no-op —
the `resolve` job skips the release when the resolved version is already tagged.

Apps still on the tag trigger keep working: a caller that runs `on: push: tags`
and passes `version` explicitly always releases, exactly as before.

Caller examples (in an app repo):

```yaml
# .github/workflows/prepare-release.yml
name: prepare-release
on:
  workflow_dispatch:
    inputs:
      version: { description: "X.Y.Z", required: true, type: string }
jobs:
  prepare-release:
    uses: apius-tech/splunk-app-ci/.github/workflows/prepare-release.yml@main
    with:
      version: ${{ inputs.version }}
      app_id: <app_id>
```

```yaml
# .github/workflows/release.yml — merging the Release PR triggers the release.
name: release
on:
  push:
    branches: [main]
jobs:
  release:
    # contents: write is needed to create the tag and the GitHub Release; the
    # repo default is read-only and a reusable workflow cannot exceed its
    # caller's grant.
    permissions:
      contents: write
    uses: apius-tech/splunk-app-ci/.github/workflows/release.yml@main
    with:
      app_id: <app_id>
      # version omitted on purpose: read from the stamped app.conf, and the
      # release is skipped when that version is already tagged.
      splunk_versions: "9.2,9.3,9.4,10.0"   # declare real compatibility
      splunkbase_app_id: ${{ vars.SPLUNKBASE_APP_ID }}
    secrets: inherit
```

The `prepare-release` job needs the repo setting "Allow GitHub Actions to
create and approve pull requests" enabled so it can open the Release PR.

## Development

```
uv run --with pytest pytest -q
ruff check .
ruff format --check .
```
