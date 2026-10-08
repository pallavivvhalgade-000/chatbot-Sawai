from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from app.db.database import (
    get_connection,
)


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def link_lead_to_session(
    *,
    lead_id: str,
    session_id: str,
) -> None:
    """
    Link one persisted lead to the chatbot session
    that created it.
    """

    now = _utc_now_iso()

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO lead_conversations (
                lead_id,
                session_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(lead_id)
            DO UPDATE SET
                session_id = excluded.session_id,
                updated_at = excluded.updated_at
            """,
            (
                lead_id,
                session_id,
                now,
                now,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def get_session_id_for_lead(
    lead_id: str,
) -> str | None:
    """
    Return the chatbot session associated with a lead.
    """

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT session_id
            FROM lead_conversations
            WHERE lead_id = ?
            LIMIT 1
            """,
            (
                lead_id,
            ),
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        return None

    return row["session_id"]            