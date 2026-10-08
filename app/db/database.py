import sqlite3
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from app.core.config import settings


def get_database_path() -> Path:
    """
    Return the configured SQLite database path.
    """

    path = Path(settings.database_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    path.parent.mkdir(parents=True, exist_ok=True)

    return path


def get_connection() -> sqlite3.Connection:
    """
    Create a SQLite database connection.
    """

    connection = sqlite3.connect(
        get_database_path(),
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    """
    Create the database tables if they do not already exist.
    """

    connection = get_connection()

    try:
        # -----------------------------------------------------
        # Leads table
        # -----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                lead_id TEXT PRIMARY KEY,
                name TEXT,
                mobile TEXT,
                email TEXT,
                service TEXT,
                sub_service TEXT,
                requirement TEXT,
                budget TEXT,
                timeline TEXT,
                location TEXT,
                priority TEXT,
                status TEXT NOT NULL,
                assigned_to TEXT,
                contact_preference TEXT,
                source TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        # -----------------------------------------------------
        # Lead notification audit table
        # -----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (lead_id)
            )
            """
        )

        connection.execute(
        """
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_conversation_sessions_updated_at
            ON conversation_sessions (updated_at)
            """
        )

        # =========================================================
        # Lead audit trail
        # =========================================================

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                lead_id TEXT NOT NULL,

                event_type TEXT NOT NULL,

                old_value TEXT,
                new_value TEXT,

                actor TEXT NOT NULL,

                notes TEXT,

                created_at TEXT NOT NULL,

                FOREIGN KEY (lead_id)
                    REFERENCES leads (lead_id)
            )
            """
        )


        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_lead_events_lead_id
            ON lead_events (lead_id)
            """
        )


        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_lead_events_created_at
            ON lead_events (created_at)
            """
        )


        # =========================================================
        # Reliable notification / integration delivery queue
        # =========================================================

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_delivery_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                lead_id TEXT NOT NULL,

                channel TEXT NOT NULL,

                event_type TEXT NOT NULL,

                status TEXT NOT NULL,

                attempt_count INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,

                next_attempt_at TEXT,

                last_error TEXT,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                UNIQUE (
                    lead_id,
                    channel,
                    event_type
                ),

                FOREIGN KEY (lead_id)
                    REFERENCES leads (lead_id)
            )
            """
        )


        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_delivery_jobs_status
            ON lead_delivery_jobs (
                status,
                next_attempt_at
            )
            """
        )

        # =========================================================
        # Chatbot analytics events
        # =========================================================

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_type TEXT NOT NULL,

                session_id TEXT,
                service TEXT,

                metadata_json TEXT,

                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_analytics_events_type
            ON analytics_events (
                event_type
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_analytics_events_created_at
            ON analytics_events (
                created_at
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_conversations (
                lead_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_lead_conversations_session_id
            ON lead_conversations (
                session_id
            )
            """
        )


        # Commit both table-creation operations
        connection.commit()

    finally:
        connection.close() 


def insert_lead(lead_data: dict[str, Any]) -> None:
    """
    Insert a lead into the database.
    """

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO leads (
                lead_id,
                name,
                mobile,
                email,
                service,
                sub_service,
                requirement,
                budget,
                timeline,
                location,
                priority,
                status,
                assigned_to,
                contact_preference,
                source,
                notes,
                created_at
            )
            VALUES (
                :lead_id,
                :name,
                :mobile,
                :email,
                :service,
                :sub_service,
                :requirement,
                :budget,
                :timeline,
                :location,
                :priority,
                :status,
                :assigned_to,
                :contact_preference,
                :source,
                :notes,
                :created_at
            )
            """,
            lead_data,
        )

        connection.commit()

    finally:
        connection.close()


def get_lead(lead_id: str) -> dict[str, Any] | None:
    """
    Retrieve one lead by ID.
    """

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM leads
            WHERE lead_id = ?
            """,
            (lead_id,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def get_all_leads() -> list[dict[str, Any]]:
    """
    Retrieve all leads, newest first.
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM leads
            ORDER BY created_at DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def update_lead(
    lead_id: str,
    updates: dict[str, Any],
) -> bool:
    """
    Update selected fields of an existing lead.

    Returns True if a lead was updated.
    """

    if not updates:
        return False

    allowed_fields = {
        "name",
        "mobile",
        "email",
        "service",
        "sub_service",
        "requirement",
        "budget",
        "timeline",
        "location",
        "priority",
        "status",
        "assigned_to",
        "contact_preference",
        "source",
        "notes",
    }

    safe_updates = {
        key: value
        for key, value in updates.items()
        if key in allowed_fields
    }

    if not safe_updates:
        return False

    assignments = ", ".join(
        f"{field} = :{field}"
        for field in safe_updates
    )

    safe_updates["lead_id"] = lead_id

    connection = get_connection()

    try:
        cursor = connection.execute(
            f"""
            UPDATE leads
            SET {assignments}
            WHERE lead_id = :lead_id
            """,
            safe_updates,
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:
        connection.close()


def record_notification(
    lead_id: str,
    channel: str,
    success: bool,
    error_message: str | None = None,
) -> None:
    """
    Store the result of a notification attempt.
    """

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO lead_notifications (
                lead_id,
                channel,
                status,
                error_message,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                lead_id,
                channel,
                "sent" if success else "failed",
                error_message,
                datetime.now(
                    timezone.utc
                ).isoformat(),
            ),
        )

        connection.commit()

    finally:
        connection.close()


def has_successful_notification(
    lead_id: str,
) -> bool:
    """
    Prevent accidental duplicate notification delivery.
    """

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT 1
            FROM lead_notifications
            WHERE lead_id = ?
              AND status = 'sent'
            LIMIT 1
            """,
            (lead_id,),
        ).fetchone()

        return row is not None

    finally:
        connection.close()