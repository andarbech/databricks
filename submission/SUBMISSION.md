# Day 1 Homework — Lakebase-powered support app

## Application

[Open the deployed Support Desk](https://support-tickets-andarbech-7474651538933989.aws.databricksapps.com)

The app requires Databricks authentication and appropriate app access. An instructor
without access may be unable to open the URL; the screenshots and source provide
additional evidence. The stock-market app is a separate application.

## Source

- Source ZIP: `../dist/support-app-source.zip`.
- Repository URL: [Support app source — independent branch](https://github.com/andarbech/databricks/tree/codex/day1-lakebase-support).
- Branch: `codex/day1-lakebase-support`. The `main` branch remains the stock app.

## Screenshots

Pending capture from an authenticated browser:

1. `deployed-app.png`: the deployed support interface with a selected ticket and messages.
2. `lakebase-tables.png`: the Lakebase schema/table browser and sample query results.

Existing local preview images are not substitutes for a deployed screenshot.

Additional verified evidence is available in the local delivery folder as `lakebase-ticket-summary.csv`,
`lakebase-sample-records.csv`, and `lakebase-verification.json`. These are exports
of actual Lakebase query results, not screenshots of the Databricks UI.

## Reflection — proposed wording for the student to review

The most difficult part was configuring the correct application identity and PostgreSQL permissions while keeping the existing stock-market app separate. I learned that workspace administration and database role privileges are different, and that each app needs access granted to its own service principal. Lakebase is suited to operational workloads with frequent small inserts, updates, transactions, and foreign-key relationships, whereas analytics tables primarily support large scans and aggregations. I verified persistence by creating tickets, adding messages, updating statuses, and reading the saved data through a new session. Next, I would add ticket priorities and assignment to support agents so the team can organize and route requests more effectively.

## Functional verification

- Three example tickets, with two messages each and three distinct statuses.
- Tickets and messages read from Lakebase using parameterized SQL.
- Ticket creation, message creation, and status updates verified on the deployed app.
- Saved status and messages verified through a new HTTP session.
- No passwords, database connection strings, OAuth tokens, or API keys in source.
