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
```

`build_package` produces `<app_id>-<version>.tar.gz` whose single top-level
directory is the app id, with `app.conf` version stamped, vendored `lib/`
retained, and tooling/VCS artifacts excluded.

## Development

```
uv run --with pytest pytest -q
ruff check .
ruff format --check .
```
