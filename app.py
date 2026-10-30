"""Support application: tickets, conversations, and status updates backed by Lakebase."""

import os

from flask import Flask, jsonify, request, render_template
from werkzeug.exceptions import HTTPException

import lakebase

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error=error.description), error.code


@app.after_request
def response_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'"
    )
    return response


@app.get("/")
def index():
    return render_template("index.html")


@app.patch("/tickets/<int:ticket_id>")
def change_ticket_status(ticket_id):
    if not 1 <= ticket_id <= 9223372036854775807:
        return jsonify(error="The ticket ID is outside the supported range."), 400
    if not request.is_json:
        return jsonify(error="Send the request body as application/json."), 415
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"status"}:
        return jsonify(error="Provide a JSON object containing only status."), 400
    status = payload["status"]
    if not isinstance(status, str) or status not in ("open", "in_progress", "resolved"):
        return jsonify(error="Status must be open, in_progress, or resolved."), 400
    try:
        if not current_author():
            return jsonify(error="An authenticated user identity is required."), 401
        row = lakebase.update_ticket_status(ticket_id, status)
    except Exception as error:
        app.logger.error("Failed to update status: %s", type(error).__name__)
        return jsonify(error="The status could not be updated. Refresh before retrying."), 503
    if row is None:
        return jsonify(error="The ticket does not exist."), 404
    row["created_at"] = row["created_at"].isoformat()
    return jsonify(ticket=row)


def current_author():
    if os.environ.get("DATABRICKS_APP_NAME") or os.environ.get("DATABRICKS_CLIENT_ID"):
        # Trust this header only behind the Databricks Apps authentication proxy.
        return request.headers.get("X-Forwarded-Email", "").strip() or None
    # Local requests use the selected OAuth identity, ignoring author input.
    return lakebase.get_client().current_user.me().user_name


@app.post("/tickets")
def new_ticket():
    if not request.is_json:
        return jsonify(error="Send the request body as application/json."), 415
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="The request body must be a valid JSON object."), 400
    if set(payload) - {"title"}:
        return jsonify(error="Only title is accepted. Identity and status are assigned by the server."), 400
    title = payload.get("title")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200 or "\x00" in title:
        return jsonify(error="Title must contain between 1 and 200 characters."), 400

    try:
        author = current_author()
        if not author:
            return jsonify(error="An authenticated user identity is required."), 401
        row = lakebase.create_ticket(title.strip(), author)
    except Exception as error:
        app.logger.error("Failed to create a ticket: %s", type(error).__name__)
        return jsonify(error="The ticket could not be created. Check the ticket list before retrying."), 503

    row["created_at"] = row["created_at"].isoformat()
    response = jsonify(ticket=row)
    response.status_code = 201
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/tickets/<int:ticket_id>/messages")
def new_message(ticket_id):
    if not 1 <= ticket_id <= 9223372036854775807:
        return jsonify(error="The ticket ID is outside the supported range."), 400
    if not request.is_json:
        return jsonify(error="Send the request body as application/json."), 415
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="The request body must be a valid JSON object."), 400
    if set(payload) - {"message_text"}:
        return jsonify(error="Only message_text is accepted. The author is assigned by the server."), 400
    message_text = payload.get("message_text")
    if (not isinstance(message_text, str)
            or not 1 <= len(message_text.strip()) <= 10000
            or "\x00" in message_text):
        return jsonify(error="Message text must contain between 1 and 10000 characters."), 400

    try:
        author = current_author()
        if not author:
            return jsonify(error="An authenticated user identity is required."), 401
        row = lakebase.create_message(ticket_id, message_text.strip(), author)
    except Exception as error:
        app.logger.error("Failed to create a message: %s", type(error).__name__)
        return jsonify(error="The message could not be added. Check the conversation before retrying."), 503

    if row is None:
        return jsonify(error="The ticket does not exist."), 404
    row["created_at"] = row["created_at"].isoformat()
    response = jsonify(message=row)
    response.status_code = 201
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/healthz")
def healthz():
    # Check the web process; /tickets also checks Lakebase access.
    return jsonify(status="ok")


@app.get("/tickets")
def tickets():
    try:
        rows = lakebase.list_tickets()
    except Exception as error:
        # Never return queries, connection details, or credentials to the browser.
        app.logger.error("Failed to fetch tickets: %s", type(error).__name__)
        return jsonify(error="Tickets could not be loaded. Please try again."), 503

    for row in rows:
        row["created_at"] = row["created_at"].isoformat()
    response = jsonify(tickets=rows)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/tickets/<int:ticket_id>/messages")
def ticket_messages(ticket_id):
    if not 1 <= ticket_id <= 9223372036854775807:
        return jsonify(error="The ticket ID is outside the supported range."), 400

    try:
        rows = lakebase.list_ticket_messages(ticket_id)
    except Exception as error:
        app.logger.error("Failed to fetch messages: %s", type(error).__name__)
        return jsonify(error="Messages could not be loaded. Please try again."), 503

    if rows is None:
        return jsonify(error="The ticket does not exist."), 404

    for row in rows:
        row["created_at"] = row["created_at"].isoformat()
    response = jsonify(ticket_id=ticket_id, messages=rows)
    response.headers["Cache-Control"] = "no-store"
    return response
