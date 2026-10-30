"""Shared Lakebase access with OAuth and connection pooling."""

import os
from functools import lru_cache

import psycopg
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from sqlalchemy import create_engine, text


@lru_cache(maxsize=1)
def get_client():
    # Locally, Config uses DATABRICKS_CONFIG_PROFILE; in Apps, it uses the app identity.
    return WorkspaceClient(config=Config())


@lru_cache(maxsize=1)
def get_engine():
    client = get_client()
    endpoint_path = os.environ["LAKEBASE_ENDPOINT"]
    host = os.environ.get("PGHOST")
    if not host:
        host = client.postgres.get_endpoint(name=endpoint_path).status.hosts.host
    database = os.environ.get("PGDATABASE", "databricks_postgres")
    username = os.environ.get("PGUSER")
    if not username:
        if os.environ.get("DATABRICKS_APP_NAME") or os.environ.get("DATABRICKS_CLIENT_ID"):
            raise RuntimeError("The app requires PGUSER to be configured with its PostgreSQL role")
        username = client.current_user.me().user_name

    def connect():
        # Request a fresh token for each physical connection; never store tokens on disk.
        # The pool can reuse authenticated connections after their login token expires.
        credential = client.postgres.generate_database_credential(endpoint=endpoint_path)
        return psycopg.connect(
            host=host,
            port=int(os.environ.get("PGPORT", "5432")),
            dbname=database,
            user=username,
            password=credential.token,
            sslmode="require",
            connect_timeout=15,
            options="-c statement_timeout=15000 -c timezone=UTC",
        )

    return create_engine(
        "postgresql+psycopg://",
        creator=connect,
        pool_size=3,
        max_overflow=2,
        pool_timeout=20,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


def list_tickets():
    # Do not create schemas or tables: migrations have already been applied separately.
    with get_engine().connect() as connection:
        rows = connection.execute(text("""
            SELECT ticket_id, title, status, created_by, created_at
            FROM support_app.tickets
            ORDER BY created_at DESC, ticket_id DESC
        """)).mappings()
        return [dict(row) for row in rows]


def list_ticket_messages(ticket_id: int):
    # LEFT JOIN distinguishes an empty ticket from a ticket that does not exist.
    # Read both tables in the same snapshot using a single query.
    with get_engine().connect() as connection:
        rows = connection.execute(text("""
            SELECT m.message_id, m.ticket_id, m.message_text, m.author, m.created_at
            FROM support_app.tickets AS t
            LEFT JOIN support_app.ticket_messages AS m ON m.ticket_id = t.ticket_id
            WHERE t.ticket_id = :ticket_id
            ORDER BY m.created_at ASC, m.message_id ASC
        """), {"ticket_id": ticket_id}).mappings().all()
        if not rows:
            return None
        return [dict(row) for row in rows if row["message_id"] is not None]


def create_ticket(title: str, created_by: str):
    # begin() commits on success and rolls back if an operation raises an error.
    with get_engine().begin() as connection:
        row = connection.execute(text("""
            INSERT INTO support_app.tickets (title, created_by)
            VALUES (:title, :created_by)
            RETURNING ticket_id, title, status, created_by, created_at
        """), {"title": title, "created_by": created_by}).mappings().one()
        return dict(row)


def create_message(ticket_id: int, message_text: str, author: str):
    with get_engine().begin() as connection:
        # Keep the parent ticket from being deleted between the check and insert.
        # The row lock is released when this transaction commits or rolls back.
        ticket = connection.execute(text("""
            SELECT ticket_id FROM support_app.tickets
            WHERE ticket_id = :ticket_id
            FOR KEY SHARE
        """), {"ticket_id": ticket_id}).first()
        if ticket is None:
            return None
        row = connection.execute(text("""
            INSERT INTO support_app.ticket_messages (ticket_id, message_text, author)
            VALUES (:ticket_id, :message_text, :author)
            RETURNING message_id, ticket_id, message_text, author, created_at
        """), {
            "ticket_id": ticket_id,
            "message_text": message_text,
            "author": author,
        }).mappings().one()
        return dict(row)


def update_ticket_status(ticket_id: int, status: str):
    with get_engine().begin() as connection:
        row = connection.execute(text("""
            UPDATE support_app.tickets SET status = :status
            WHERE ticket_id = :ticket_id
            RETURNING ticket_id, title, status, created_by, created_at
        """), {"ticket_id": ticket_id, "status": status}).mappings().first()
        return dict(row) if row is not None else None
