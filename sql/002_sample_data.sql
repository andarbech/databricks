-- Fictional sample data. Apply once to empty tables.
-- Retrieve actual IDs with RETURNING; do not assume they start at 1.
BEGIN;

-- Prevent concurrent writes during the initial check and seed operation.
LOCK TABLE support_app.tickets, support_app.ticket_messages
    IN SHARE ROW EXCLUSIVE MODE;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM support_app.tickets)
       OR EXISTS (SELECT 1 FROM support_app.ticket_messages) THEN
        RAISE EXCEPTION 'Initial load cancelled: the tables already contain data';
    END IF;
END;
$$;

WITH new_ticket AS (
    INSERT INTO support_app.tickets (title, status, created_by)
    VALUES ('Unable to access the internal portal', 'open', 'ana@example.com')
    RETURNING ticket_id
)
INSERT INTO support_app.ticket_messages (ticket_id, message_text, author)
SELECT ticket_id, message_text, author
FROM new_ticket
CROSS JOIN (VALUES
    ('The portal has displayed a sign-in error since this morning.', 'ana@example.com'),
    ('We have received your report. Does this also happen in another browser?', 'support@example.com')
) AS messages(message_text, author);

WITH new_ticket AS (
    INSERT INTO support_app.tickets (title, status, created_by)
    VALUES ('The sales report is taking too long', 'in_progress', 'bruno@example.com')
    RETURNING ticket_id
)
INSERT INTO support_app.ticket_messages (ticket_id, message_text, author)
SELECT ticket_id, message_text, author
FROM new_ticket
CROSS JOIN (VALUES
    ('The monthly report has been running for more than ten minutes.', 'bruno@example.com'),
    ('We are reviewing the execution plan and date filters.', 'support@example.com')
) AS messages(message_text, author);

WITH new_ticket AS (
    INSERT INTO support_app.tickets (title, status, created_by)
    VALUES ('Documentation access request', 'resolved', 'carla@example.com')
    RETURNING ticket_id
)
INSERT INTO support_app.ticket_messages (ticket_id, message_text, author)
SELECT ticket_id, message_text, author
FROM new_ticket
CROSS JOIN (VALUES
    ('I need permission to read the team documentation.', 'carla@example.com'),
    ('Access has been granted and you have confirmed that it works.', 'support@example.com')
) AS messages(message_text, author);

COMMIT;
