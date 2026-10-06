import logging
from datetime import datetime, timezone

from app.db.database import get_connection
from app.domain.state import ConversationState


logger = logging.getLogger(__name__)


def _utc_now() -> str:
    """
    Return the current UTC time as an ISO-formatted string.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


def get_session(
    session_id: str,
) -> ConversationState | None:
    """
    Load a conversation session from SQLite.

    Returns None when the session does not exist.
    """

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT state_json
            FROM conversation_sessions
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

    finally:
        connection.close()


    if row is None:
        return None


    try:
        return ConversationState.model_validate_json(
            row["state_json"]
        )

    except Exception as exc:
        logger.exception(
            "Unable to restore conversation session %s",
            session_id,
        )

        raise RuntimeError(
            f"Unable to restore conversation session {session_id}"
        ) from exc


def save_session(
    state: ConversationState,
) -> ConversationState:
    """
    Insert or update a conversation session.

    The complete Pydantic ConversationState is serialized
    to JSON so enums, nested models, contact details,
    qualification fields, navigation state, and metadata
    can be restored after a server restart.
    """

    now = _utc_now()

    state_json = state.model_dump_json()


    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO conversation_sessions (
                session_id,
                state_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(session_id)
            DO UPDATE SET
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (
                state.session_id,
                state_json,
                now,
                now,
            ),
        )

        connection.commit()

    finally:
        connection.close()


    return state


def create_session() -> ConversationState:
    """
    Create and immediately persist a new conversation.
    """

    state = ConversationState()

    save_session(state)

    return state


def delete_session(
    session_id: str,
) -> bool:
    """
    Delete a persisted conversation session.

    Not currently used by the widget reset button, but
    provided for future retention/cleanup functionality.
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            DELETE FROM conversation_sessions
            WHERE session_id = ?
            """,
            (session_id,),
        )

        connection.commit()

        deleted = cursor.rowcount > 0

    finally:
        connection.close()


    return deleted