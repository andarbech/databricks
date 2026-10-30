# Deploy the separate support app

## Two independent applications

- Stock Watchlist: `lakebase-andarbech-app` (original GitHub stock application).
- Support Desk: `support-tickets-andarbech` (this directory).

The deployment helper targets Support Desk by default and blocks deployment to the
stock application. Both use the existing Lakebase project and production branch;
support data is isolated in the `support_app` schema. Do not rerun the initial schema
or sample-data scripts: the data already exists.

## Runtime configuration

`app.yaml` starts Gunicorn using `DATABRICKS_APP_PORT`. A managed `postgres` resource
injects `PGHOST`, `PGPORT`, `PGDATABASE`, and `PGUSER`. `LAKEBASE_ENDPOINT` uses
`valueFrom: postgres`, which resolves to the endpoint resource path. The SDK uses
the support app's own service principal and generates temporary database credentials.
There are no passwords or Massive API keys in this application's configuration.

The support app role needs schema USAGE, SELECT/INSERT/UPDATE on both support tables,
and USAGE on the two identity sequences. The schema remains owned by `student`;
the app never runs DDL. PostgreSQL grants and workspace permissions are distinct.

## Preview and redeploy

From this directory:

```bash
# Read-only preview
.venv/bin/python scripts/deploy.py --profile dataexpert_course

# Deploy to support-tickets-andarbech
.venv/bin/python scripts/deploy.py --profile dataexpert_course --apply
```

The helper preserves existing resources, attaches the selected Lakebase branch and
database if needed, uploads only runtime files to a new workspace release directory,
and deploys those files to the support app. It never pushes to GitHub. Existing
workspace releases remain available. With `--json`, `create-update` requires
`update_mask` inside the request body despite the CLI's positional help text.

Support app URL:
https://support-tickets-andarbech-7474651538933989.aws.databricksapps.com

Stock app URL:
https://lakebase-andarbech-app-7474651538933989.aws.databricksapps.com

Useful commands:

```bash
databricks apps get support-tickets-andarbech --profile dataexpert_course
databricks apps logs support-tickets-andarbech --profile dataexpert_course
```

## Validation and packaging

CLI v1.23.0 `databricks apps validate` only detects Node projects. For this Flask
project use the real Lakebase integration tests in TESTING.md, Python compilation,
JavaScript syntax checks, and browser acceptance checks.

```bash
.venv/bin/python scripts/package_source.py
```

The source ZIP is `dist/support-app-source.zip`. It excludes credentials, local
configuration, virtual environments, caches, and preview images. Runtime versions
are pinned in `requirements.lock.txt`. Rebuild the archive after editing source.

## Access model

Users with app access share the support workspace. The support service principal
accesses PostgreSQL; the authenticated user's email is recorded on tickets/messages.
This is not per-user row isolation. The Databricks authentication proxy must remain
in front of the app. Writes accept JSON and never accept caller-supplied authors.
Status updates use last-write-wins semantics. Follow TESTING.md before submission.
