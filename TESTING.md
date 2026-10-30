# Verification and submission checklist

## Local integration tests

Authenticate with OAuth, then run from the project directory:

```bash
export DATABRICKS_CONFIG_PROFILE=dataexpert_course
export LAKEBASE_ENDPOINT=projects/dataexpertionewdb/branches/production/endpoints/primary
.venv/bin/python -m unittest discover -s tests -v
```

These tests use real Lakebase. They temporarily commit a ticket and message,
verify persistence through a new connection, and remove only their own records.
Use the project owner's local profile because cleanup needs DELETE privileges;
the app role intentionally has no DELETE privilege. Sequence gaps are expected.
Never run these tests with an unrelated production database.

Start a local preview:

```bash
.venv/bin/gunicorn --config gunicorn.conf.py app:app
```

Open http://localhost:8000. Local writes record the OAuth profile's identity.

## Deployed app acceptance test

- [ ] Open the app URL while signed into Databricks.
- [ ] Confirm the three example tickets load and counts match their statuses.
- [ ] Filter by each status; clear the filter to restore the full list.
- [ ] Select a sample ticket and confirm its two messages load.
- [ ] Create a ticket titled `Deployment verification`.
- [ ] Confirm its initial status is Open and its conversation is empty.
- [ ] Add a message and confirm the recorded author matches your identity.
- [ ] Change the status to In progress, then Resolved.
- [ ] Refresh the entire browser page, select the ticket again, and confirm its
      title, messages, and status persist.
- [ ] Try a blank title/message and confirm the interface reports the problem.
- [ ] Check the layout on desktop and a narrow/mobile viewport.
- [ ] Check app logs for authentication or permission failures.

Local tests cannot replace the deployed test: the app uses its own service principal
instead of the developer's OAuth identity. On permission failure, check the resource
attachment, `PGUSER`, schema USAGE, table privileges, and identity sequence USAGE.

## Lakebase screenshot

In the Lakebase SQL editor, choose project `new-database`, branch `production`, and
PostgreSQL database `databricks_postgres`. Execute this PostgreSQL query:

```sql
SELECT t.ticket_id, t.title, t.status, t.created_by,
       m.message_id, m.message_text, m.author, m.created_at
FROM support_app.tickets AS t
JOIN support_app.ticket_messages AS m ON m.ticket_id = t.ticket_id
ORDER BY t.ticket_id, m.created_at, m.message_id;
```

Capture the schema/table browser and sample rows without showing connection strings,
passwords, tokens, or other secrets. Take the app screenshot after the deployed test.
A local preview screenshot does not satisfy the deployed screenshot requirement.

## Submission

- [ ] Deployed app URL.
- [ ] `dist/support-app-source.zip`.
- [ ] Screenshot of the deployed app.
- [ ] Screenshot of Lakebase tables and example records.
- [ ] Your own 3–5 sentence reflection: hardest part; OLTP vs analytics storage;
      and the feature you would add next.

Suggested reflection structure (replace with your experience):

1. The hardest part was … because …
2. I resolved it by …
3. Lakebase suits this workflow because …, whereas an analytics table is optimized for …
4. Next, I would add … to help …

## Latest local verification

- Four integration tests passed against real Lakebase, covering the complete write
  workflow, persistence after reconnect, invalid requests, missing tickets, and assets.
- A real Chromium browser verified ticket creation, literal HTML rendering, message
  creation, status changes, full-page refresh, and persisted data through the UI.
- Desktop and 390-pixel mobile layouts were checked; there were no JavaScript errors
  or mobile horizontal overflow. Status filtering returned the expected sample ticket.
- Local preview images are `local-preview.png` and `mobile-preview.png`; these are
  development previews, not evidence of a deployed application.
- Python compilation, JavaScript syntax, and a read-only deployment preview passed.
- `databricks apps validate` does not support this Python project in CLI v1.23.0.
- Deployed app-identity connectivity verified: health and listing returned 200; ticket
  creation and message creation returned 201; status update returned 200. A new HTTP
  session confirmed the saved status and message. Temporary test records were removed.
- The final signed-in browser review and submission screenshots remain pending.

## Separate support application

The support deployment target is `support-tickets-andarbech`. The original stock
app remains `lakebase-andarbech-app`, unchanged by this separate deployment.
Use the support URL for the submission and screenshots:
https://support-tickets-andarbech-7474651538933989.aws.databricksapps.com
