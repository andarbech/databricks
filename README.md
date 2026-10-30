# Day 1 — Lakebase-powered support application

## Environment

| Resource | Value |
|---|---|
| CLI profile | `dataexpert_course` |
| Support Databricks App | `support-tickets-andarbech` |
| Separate stock app (preserved) | `lakebase-andarbech-app` |
| Lakebase project | `dataexpertionewdb` (display name: `new-database`) |
| Branch | `production` |
| PostgreSQL database | `databricks_postgres` |
| Schema | `support_app` |

## Database setup

`sql/001_support_schema.sql` was applied on October 30, 2026, using the
user-authorized `student` role. That role owns the schema and tables. Application
startup must not run schema migrations. Future schema changes require the owner.

The support application's own OAuth role maps to its separate service principal.
It has `USAGE` on the schema, `SELECT`, `INSERT`, and `UPDATE` on both tables, and
`USAGE` on their identity sequences. It has no superuser, `CREATEDB`, `CREATEROLE`,
or `BYPASSRLS` privileges. PostgreSQL role administration is separate from workspace
administration; the local user could not assume this role during the initial attempt.

`sql/002_sample_data.sql` inserted three fictional tickets and six messages in one
transaction using the local OAuth profile. Each ticket has two messages, with
statuses `open`, `in_progress`, and `resolved`. The seed script rejects nonempty
tables to prevent duplicate records. Persistence was verified from a new connection.

`sql/003_translate_sample_data.sql` translates the original sample records into
English by matching their previous values. Spanish literals in this migration are
intentional lookup values, not application copy. IDs and timestamps are preserved.
This translation migration has been applied to Lakebase using OAuth.

### Modeling decisions

- One ticket has zero or more messages; each message belongs to exactly one ticket.
- `BIGINT GENERATED ALWAYS AS IDENTITY` assigns IDs safely during concurrent writes.
  Never calculate `MAX(id) + 1`. Gaps after failed or rolled-back inserts are expected.
- Primary keys enforce unique, non-null identifiers.
- The foreign key prevents orphan messages. `ON DELETE RESTRICT` prevents deleting
  a ticket while it still has messages.
- `NOT NULL` rejects nulls; `CHECK` constraints also reject empty titles, empty
  messages, and invalid statuses. Application validation provides useful errors.
- New tickets default to `open` in PostgreSQL.
- `TIMESTAMPTZ` represents an instant; the API returns ISO 8601 timestamps in UTC.
- The `(ticket_id, created_at, message_id)` index supports stable message ordering.
- Migration transactions prevent partially applied changes. Apply the initial
  migration once; subsequent changes belong in new migrations.

## Python backend

- `app.py`: routes, validation, identity resolution, JSON responses.
- `lakebase.py`: OAuth, SQLAlchemy connection pool, parameterized SQL.
- `requirements.txt`: Python dependencies.
- A token is requested for each new physical connection and never written to disk.
  Authenticated connections can be reused after their login token expires.
- Pool health checks and recycling handle stale connections.
- No schema DDL runs on startup. No password connection string is stored in source.
- Database access uses the app identity after deployment. Locally, `Config()` uses
  the selected OAuth profile.

### Routes

| Method | Route | Behavior |
|---|---|---|
| GET | `/healthz` | Check the web process without querying Lakebase |
| GET | `/tickets` | Read all tickets, newest first |
| GET | `/tickets/<ticket_id>/messages` | Read a conversation chronologically |
| POST | `/tickets` | Create a ticket from a JSON object containing `title` |
| POST | `/tickets/<ticket_id>/messages` | Add a message from JSON containing `message_text` |
| PATCH | `/tickets/<ticket_id>` | Update status from JSON containing `status` |
| GET | `/` | Interactive support workspace |

An existing ticket without messages returns `200` and `messages: []`. A missing
ticket returns `404`. A `LEFT JOIN` distinguishes these cases in one snapshot.
Numeric IDs outside the positive BIGINT range return `400`.

Creation accepts only `title` (1–200 characters after trimming). The server assigns
the authenticated author; PostgreSQL assigns the ID, timestamp, and `open` status.
In Apps, the author comes from the trusted `X-Forwarded-Email` proxy header.
Locally, it comes from the OAuth profile. Success returns `201` after commit.

Invalid JSON or fields return `400`; a non-JSON content type returns `415`.
Database failures return `503` without exposing internal details. Creation is not
yet idempotent: check the ticket list before retrying an ambiguous failure.
Request bodies are limited to 64 KiB. The listing currently returns all tickets;
add pagination when the dataset grows.

Message creation accepts only `message_text` (1–10,000 characters after trimming).
The server assigns the authenticated author and the database assigns the message ID
and timestamp. A missing ticket returns `404`; success returns `201` after commit.
`SELECT ... FOR KEY SHARE` locks the parent ticket during the transaction, preventing
concurrent deletion between the existence check and insertion. Other requests can
still add messages to the same ticket. The foreign key remains the database safeguard.
The lock is released automatically at the end of the transaction.

### Run locally

From this directory, install dependencies into an isolated virtual environment:

```bash
uv venv --python python3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
export DATABRICKS_CONFIG_PROFILE=dataexpert_course
export LAKEBASE_ENDPOINT=projects/dataexpertionewdb/branches/production/endpoints/primary
.venv/bin/gunicorn app:app --bind 127.0.0.1:8000 --workers 1
```

Open `http://127.0.0.1:8000/` to use the complete interface, or `/tickets` to inspect JSON.
Create a ticket with:

```bash
curl --request POST http://127.0.0.1:8000/tickets \
  --header 'Content-Type: application/json' \
  --data '{"title":"Unable to connect to the company VPN"}'
```

## Verification

Rejected inserts verified invalid status and empty title (`23514`), and a message
referencing a nonexistent ticket (`23503`). Read routes were checked against real
Lakebase data, including reconnection, message ownership, ordering, missing tickets,
and ID bounds. An empty conversation was checked with a temporary ticket in a
rolled-back transaction. No test records were retained.

Local checks use the user's OAuth profile. The deployed app identity and resource
configuration still require verification.

Ticket creation was verified against Lakebase: `201`, trimmed title, authenticated
author, database defaults, and persistence from a new physical connection. The
temporary committed ticket was removed afterward; three sample tickets and six
messages remain. Validation checks covered wrong types, empty/long titles, null
bytes, extra fields, malformed JSON, wrong content type, request size, and missing
deployed-user identity. SQL-looking title text was stored as literal data.

Message creation was also verified against Lakebase: `201`, trimmed text, correct
ticket linkage, authenticated author, UTC timestamp, and a matching conversation
after reconnecting. Invalid input, forged authors, missing identity, and nonexistent
tickets were rejected. Temporary committed records were removed afterward; the
original three tickets and six messages remain.

## Ready for deployment

All required application operations are implemented: list/select tickets, read and
add messages, create tickets, and update statuses. The responsive interface includes
status filtering, ticket counts, loading/empty/error states, safe text rendering,
and disabled submit buttons while requests are running. All application copy,
comments, and documentation are in English.

Status updates validate the three allowed values and commit before returning `200`.
Users with app access share the workspace; updates use last-write-wins semantics.
The interface records no data locally; all operational writes go to Lakebase.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the read-only deployment preview and explicit
apply command, and [TESTING.md](TESTING.md) for automated tests, deployed acceptance
checks, screenshot instructions, and the submission checklist.

The support app is deployed separately as `support-tickets-andarbech`. The original
`lakebase-andarbech-app` remains the stock-market watchlist. The deployment helper
blocks that stock app as a target. Support source is published separately on `codex/day1-lakebase-support`; the stock app remains on `main`.

## Source repository

[Support app branch](https://github.com/andarbech/databricks/tree/codex/day1-lakebase-support). The `main` branch is the separate stock-market app.

The submission draft is in `submission/SUBMISSION.md`. Database exports are kept
locally and are not published to the repository.
