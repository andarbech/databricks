-- PostgreSQL / Lakebase. Run against databricks_postgres.
-- Applied on 2026-10-30 as student at the user's request.
-- The app has explicit usage, read, insert, and update permissions.
-- Apply once; BEGIN/COMMIT prevents a partially applied migration.
BEGIN;

CREATE SCHEMA support_app;

CREATE TABLE support_app.tickets (
    ticket_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title TEXT NOT NULL CHECK (char_length(btrim(title)) BETWEEN 1 AND 200),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'in_progress', 'resolved')),
    created_by TEXT NOT NULL CHECK (char_length(btrim(created_by)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE support_app.ticket_messages (
    message_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id BIGINT NOT NULL,
    message_text TEXT NOT NULL
        CHECK (char_length(btrim(message_text)) BETWEEN 1 AND 10000),
    author TEXT NOT NULL CHECK (char_length(btrim(author)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ticket_messages_ticket_fk
        FOREIGN KEY (ticket_id)
        REFERENCES support_app.tickets (ticket_id)
        ON DELETE RESTRICT
);

-- PostgreSQL does not automatically index the referencing foreign key column.
-- This index supports fetching ticket messages in a stable order.
CREATE INDEX ticket_messages_ticket_created_idx
    ON support_app.ticket_messages (ticket_id, created_at, message_id);

COMMIT;
